#### Issues

Issues are lightweight, project-scoped tracking for the work that comes out of your telemetry, such as a recurring error worth fixing or a latency regression to investigate. Create them by hand from any execution page, promote an error group into one, or let a firing alert open one automatically. An issue links to the request, error, job, or trace it came from, so anyone opening it later has the telemetry in context, not only a description of it.

Every issue linked to telemetry opens with its **incident record**: what it was about (the error class, route, or job, and the alert rule that raised it), when it started and ended, the release it came in with, who it reached - users, and the customer companies behind their email domains - and the release that fixed it, on one timeline. **Copy summary** puts the whole record on your clipboard as plain text, for the postmortem, the status update, or the note to a customer.

<figure><img src="https://www.observe.nestjs.com/docs/issues/incident-record.webp" alt="Incident record" /></figure>

An issue promoted from an error group also answers **Did a release fix this?** Pick a release, and the answer is judged on that release's own requests, on the routes the error failed on, against how often it failed there before: **Fixed**, **Not fixed**, **Too early to tell**, or **Not enough data**. It shows the error groups first seen in the release on the same routes too, because a fix that only moved where the error is thrown gives it a new fingerprint. The counts come from request rows, which are never sampled, so the answer is there as soon as the release has served enough of those routes. An agent asks the same question with `verify_fix`.

When you mark an issue resolved and it names something measurable (an operation, an alert rule's scope), the dashboard watches that operation's telemetry against its pre-incident baseline and tells you whether the fix held. It moves the issue to **Verifying**, then either closes it on its own or moves it back to **Open** with the reading that broke it. After 7 days with nothing conclusive - usually too little traffic to judge - it says so with **Unverified**, and you close the issue by hand. If you name the release the fix shipped in (your `serviceVersion`), verification waits until that release shows up in telemetry.

#### A worked path through the dashboard

The views are designed to be used in order. A typical investigation:

1. An alert fires, or the **Requests** chart shows p95 climbing.
2. Sort the route list by duration or failure rate to find which operation moved.
3. Open the operation. Is it constant or spiky? Did it start at a deploy? Check **Releases**, and the release's verdict.
4. Open a single execution from the tail of the distribution, e.g., one the baseline card calls _slower than 95% of calls_.
5. Read the **waterfall**: which span holds the self time?
6. If it failed, read the **error card** - stack trace and the source lines around the throw.
7. Check the **logs** for that trace, hovering lines to line them up with the spans.
8. **Copy the agent prompt** and hand the whole thing to a coding agent, or open an **issue** linked to the execution so whoever picks it up starts where you stopped.

The same path is available to an agent over the [MCP server](/observability/mcp-server), one tool per step, when you'd rather ask questions than click through views.
