import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { PipelineEvent, QueryResponse } from "../../types/api";
import { RouterContext } from "../../services/router";
import { createConversation, loadConversations, loadMessages } from "../../services/storage";

type Callbacks = {
  onStage: (e: PipelineEvent) => void;
  onToken: (t: string) => void;
  onDone: (r: QueryResponse) => void;
  onError: (e: string) => void;
};

const streams: { question: string; callbacks: Callbacks; abort: ReturnType<typeof vi.fn> }[] = [];

vi.mock("../../services/api", () => ({
  buildChatHistory: () => [],
  // Like the real streamQueryPipeline, callbacks stop firing once aborted.
  streamQueryPipeline: (question: string, callbacks: Callbacks) => {
    let cancelled = false;
    const guard =
      <A extends unknown[]>(fn: (...args: A) => void) =>
      (...args: A) => {
        if (!cancelled) fn(...args);
      };
    const abort = vi.fn(() => {
      cancelled = true;
    });
    streams.push({
      question,
      abort,
      callbacks: {
        onStage: guard(callbacks.onStage),
        onToken: guard(callbacks.onToken),
        onDone: guard(callbacks.onDone),
        onError: guard(callbacks.onError),
      },
    });
    return abort;
  },
}));

// Imported after the mock so ChatView picks up the fake stream.
const { ChatView } = await import("./ChatView");

const response = (answer: string): QueryResponse => ({
  answer,
  facts_used: [],
  tokens_used: 1,
  naive_rag_tokens: 2,
  compression_rate: 0.5,
  avg_sdh_score: 0.5,
  latency_ms: 1,
});

const stage = (n: 4 | 5): PipelineEvent => ({
  stage: n,
  stage_name: `stage ${n}`,
  status: "complete",
  detail: "",
  count: 0,
  error: null,
});

let lastNavigate: ReturnType<typeof vi.fn> = vi.fn();

function renderChat(): void {
  const navigate = vi.fn();
  lastNavigate = navigate;
  render(
    <RouterContext.Provider
      value={{ path: "/chat", activeTab: "chat", navigate, navigateToTab: vi.fn() }}
    >
      <ChatView />
    </RouterContext.Provider>,
  );
}

function ask(text: string) {
  const box = screen.getByRole("textbox");
  fireEvent.change(box, { target: { value: text } });
  fireEvent.keyDown(box, { key: "Enter" });
}

describe("ChatView streaming", () => {
  beforeEach(() => {
    streams.length = 0;
  });

  it("saves the answer and its pipeline events into the conversation", () => {
    renderChat();
    ask("What happened?");
    expect(streams).toHaveLength(1);
    const [conv] = loadConversations();

    act(() => {
      streams[0]!.callbacks.onStage(stage(4));
      streams[0]!.callbacks.onStage(stage(5));
      streams[0]!.callbacks.onDone(response("It rose."));
    });

    const saved = loadMessages(conv!.id);
    expect(saved.map((m) => m.role)).toEqual(["user", "ai"]);
    expect(saved[1]!.content).toBe("It rose.");
    expect(saved[1]!.pipeline_events.map((e) => e.stage)).toEqual([4, 5]);
  });

  it("aborts the stream when switching conversation and never writes into the other one", () => {
    const first = createConversation("First chat");
    const second = createConversation("Other chat");
    renderChat();
    // createConversation made `second` the active one; ask there.
    ask("question for second");
    expect(streams).toHaveLength(1);

    fireEvent.click(screen.getByText(first.title));
    expect(streams[0]!.abort).toHaveBeenCalled();

    // A late answer from the aborted stream must not land anywhere.
    act(() => streams[0]!.callbacks.onDone(response("late answer")));
    expect(loadMessages(first.id).map((m) => m.content)).not.toContain("late answer");
    expect(loadMessages(second.id).map((m) => m.content)).not.toContain("late answer");
  });

  it("records an error message when the stream fails", () => {
    renderChat();
    ask("q");
    const [conv] = loadConversations();
    act(() => streams[0]!.callbacks.onError("backend down"));
    const saved = loadMessages(conv!.id);
    expect(saved.at(-1)!.content).toContain("backend down");
  });
});

describe("ChatView sessions and focus", () => {
  beforeEach(() => {
    streams.length = 0;
  });

  it("does not store a new session until its first message is sent", () => {
    createConversation("Existing");
    renderChat();
    fireEvent.click(screen.getByText("New Session"));
    expect(loadConversations().map((c) => c.title)).toEqual(["Existing"]);

    // A second click on the empty draft does not stack up more drafts.
    fireEvent.click(screen.getByText("New Session"));
    ask("Revenue in 2021");
    const convs = loadConversations();
    expect(convs.map((c) => c.title)).toEqual(["Revenue in 2021", "Existing"]);
    expect(loadMessages(convs[0]!.id).map((m) => m.content)).toEqual(["Revenue in 2021"]);
    expect(lastNavigate).toHaveBeenCalledWith(`/chat/${convs[0]!.id}`, { replace: true });
  });

  it("starts without any stored session on first run", () => {
    renderChat();
    expect(loadConversations()).toEqual([]);
  });

  it("puts the cursor back in the chat bar when the answer arrives", () => {
    renderChat();
    ask("What happened?");
    const box = screen.getByRole("textbox");
    box.blur();
    act(() => streams[0]!.callbacks.onDone(response("It rose.")));
    expect(document.activeElement).toBe(box);
  });

  it("puts the cursor back in the chat bar after a failed answer", () => {
    renderChat();
    ask("q");
    const box = screen.getByRole("textbox");
    box.blur();
    act(() => streams[0]!.callbacks.onError("backend down"));
    expect(document.activeElement).toBe(box);
  });
});
