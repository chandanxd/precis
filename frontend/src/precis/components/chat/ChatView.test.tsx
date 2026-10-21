import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { PipelineEvent, QueryResponse } from "../../types/api";
import { RouterContext } from "../../services/router";
import {
  createConversation,
  loadConversations,
  loadMessages,
  renameConversation,
  saveMessages,
  setPageConversationId,
} from "../../services/storage";

type Callbacks = {
  onStage: (e: PipelineEvent) => void;
  onToken: (t: string) => void;
  onDone: (r: QueryResponse) => void;
  onError: (e: string) => void;
};

const streams: { question: string; callbacks: Callbacks; abort: ReturnType<typeof vi.fn> }[] = [];

// What the fake title endpoint answers (null = it failed).
let nextTitle: string | null = null;
const titleRequests: { question: string; answer: string }[] = [];

vi.mock("../../services/api", () => ({
  buildChatHistory: () => [],
  fetchChatTitle: async (question: string, answer: string) => {
    titleRequests.push({ question, answer });
    return nextTitle;
  },
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

function renderChat(conversationId?: string): void {
  const navigate = vi.fn();
  lastNavigate = navigate;
  render(
    <RouterContext.Provider
      value={{
        path: "/chat",
        activeTab: "chat",
        ...(conversationId ? { conversationId } : {}),
        navigate,
        navigateToTab: vi.fn(),
      }}
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
    // Every test starts as a fresh page load.
    setPageConversationId(null);
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
    // Already on `second` in this page load (e.g. back from another tab); ask there.
    setPageConversationId(second.id);
    renderChat();
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
    // Every test starts as a fresh page load.
    setPageConversationId(null);
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

  it("opens a fresh page load on a new session, even with an old chat in the URL", () => {
    const old = createConversation("Old chat");
    saveMessages(old.id, [
      {
        id: "m1",
        role: "user",
        content: "old question",
        timestamp: "",
        pipeline_events: [],
      } as never,
    ]);
    renderChat(old.id);
    expect(screen.queryByText("old question")).toBeNull();
    expect(lastNavigate).toHaveBeenCalledWith("/chat", { replace: true });
  });

  it("reopens the same chat when coming back to the Chat tab", () => {
    renderChat();
    ask("first question");
    act(() => streams[0]!.callbacks.onDone(response("first answer")));
    cleanup(); // leave the Chat tab

    renderChat();
    expect(screen.getByText("first answer")).toBeTruthy();
  });

  it("copies a question from its hover button", async () => {
    const writeText = vi.fn(async () => {});
    vi.stubGlobal("navigator", { ...navigator, clipboard: { writeText } });
    renderChat();
    ask("copy me");
    fireEvent.click(screen.getByLabelText("Copy message"));
    expect(writeText).toHaveBeenCalledWith("copy me");
    vi.unstubAllGlobals();
  });
});

describe("ChatView titles", () => {
  beforeEach(() => {
    streams.length = 0;
    titleRequests.length = 0;
    nextTitle = null;
    setPageConversationId(null);
  });

  const answerFirst = async (answer = "Pawns move forward.") => {
    await act(async () => {
      streams[0]!.callbacks.onDone(response(answer));
    });
  };

  it("names a new chat with the model's title after the first answer", async () => {
    nextTitle = "Chess Piece Movements";
    renderChat();
    ask("how do the chess pieces move around the board");
    expect(loadConversations()[0]!.title).toBe("how do the chess pieces");
    await answerFirst();
    expect(titleRequests).toEqual([
      { question: "how do the chess pieces move around the board", answer: "Pawns move forward." },
    ]);
    expect(loadConversations()[0]!.title).toBe("Chess Piece Movements");
  });

  it("keeps the first words when no title comes back", async () => {
    renderChat();
    ask("revenue in 2021");
    await answerFirst();
    expect(loadConversations()[0]!.title).toBe("revenue in 2021");
  });

  it("keeps a name the user chose while the answer was streaming", async () => {
    nextTitle = "Model Title";
    renderChat();
    ask("revenue in 2021");
    renameConversation(loadConversations()[0]!.id, "My name");
    await answerFirst();
    expect(loadConversations()[0]!.title).toBe("My name");
  });

  it("does not retitle on later messages", async () => {
    nextTitle = "First Title";
    renderChat();
    ask("first");
    await answerFirst();
    nextTitle = "Second Title";
    ask("second");
    await act(async () => {
      streams[1]!.callbacks.onDone(response("again"));
    });
    expect(titleRequests).toHaveLength(1);
    expect(loadConversations()[0]!.title).toBe("First Title");
  });
});

describe("ChatView edit", () => {
  beforeEach(() => {
    streams.length = 0;
    setPageConversationId(null);
  });

  const answer = (i: number, text: string) =>
    act(() => streams[i]!.callbacks.onDone(response(text)));

  it("replaces a question and everything after it, then asks again", () => {
    renderChat();
    ask("first question");
    answer(0, "first answer");
    ask("second question");
    answer(1, "second answer");
    const convId = loadConversations()[0]!.id;

    fireEvent.click(screen.getAllByLabelText("Edit message")[0]!);
    const box = screen.getByLabelText("Edit your message");
    fireEvent.change(box, { target: { value: "edited question" } });
    fireEvent.keyDown(box, { key: "Enter" });

    expect(streams).toHaveLength(3);
    expect(streams[2]!.question).toBe("edited question");
    expect(loadMessages(convId).map((m) => m.content)).toEqual(["edited question"]);
    answer(2, "new answer");
    expect(loadMessages(convId).map((m) => m.content)).toEqual(["edited question", "new answer"]);
  });

  it("cancels with Escape and does not resend unchanged text", () => {
    renderChat();
    ask("only question");
    answer(0, "only answer");

    fireEvent.click(screen.getByLabelText("Edit message"));
    fireEvent.keyDown(screen.getByLabelText("Edit your message"), { key: "Escape" });
    expect(screen.queryByLabelText("Edit your message")).toBeNull();

    fireEvent.click(screen.getByLabelText("Edit message"));
    fireEvent.keyDown(screen.getByLabelText("Edit your message"), { key: "Enter" });
    expect(streams).toHaveLength(1);
  });

  it("offers no edit while an answer is streaming", () => {
    renderChat();
    ask("pending question");
    expect((screen.getByLabelText("Edit message") as HTMLButtonElement).disabled).toBe(true);
  });
});
