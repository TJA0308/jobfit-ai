# Release verification — 2026-11-15

Revision inspected: `6fa4ad1410f993688b25d23d7a0c7f2e371679f7`.

## Observed checks

- Local Python suite: 74 tests passed.
- Component DOM suite: 5 tests passed.
- The browser access host reported unavailable. Native Chrome access then timed out waiting for app approval.
- The web reader could not access the hosted Streamlit page. This does not establish whether the app is down.

## Release gate still pending

Do not describe the deployment as verified. Run the live smoke checklist in
[DEPLOYMENT.md](DEPLOYMENT.md), capture desktop and narrow layouts, and record a
short browser walkthrough using fictional samples. Verify uploads, both report
downloads, candidate switching, empty filters, and isolated browser sessions.
Record the deployed revision separately from the local revision.

The existing README GIF remains a CLI visualization. No browser screenshots or
recording were produced during this attempt. API credentials and paid rewrites
were not needed.
