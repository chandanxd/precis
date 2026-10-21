// @ts-nocheck — ported code written for a less strict TS config
import { lazy, Suspense, useEffect, useState } from "react";

const App = lazy(() => import("./App"));

export function PrecisClient() {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const loader = (
    <div className="precis-app h-screen w-screen grid place-items-center">
      <div className="precis-logo animate-pulse">P</div>
    </div>
  );
  if (!mounted) return loader;
  return (
    <Suspense fallback={loader}>
      <App />
    </Suspense>
  );
}
