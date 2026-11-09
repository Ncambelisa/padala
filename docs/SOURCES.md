# Implementation references

Official documentation consulted on November 3–4, 2026. These references support library/protocol choices; they do not certify this implementation.

- Next.js installation / App Router: https://nextjs.org/docs/app/getting-started/installation
- Next.js 16.2: https://nextjs.org/blog/next-16-2
- React versions: https://react.dev/versions
- FastAPI security guidance: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
- Azure Document Intelligence REST quickstart: https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/quickstarts/get-started-sdks-rest-api?view=doc-intel-4.0.0
- Azure receipt extraction: https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/prebuilt/receipt?view=doc-intel-4.0.0
- Mailpit Docker setup and tags: https://mailpit.axllent.org/docs/install/docker/
- Xendit Payment Sessions `POST /sessions`: https://docs.xendit.co/apidocs/create-session
- Xendit Subscriptions overview and lifecycle: https://docs.xendit.co/docs/subscriptions-overview
- Xendit Subscription Plan scheduling and update reference: https://docs.xendit.co/apidocs/create-recurring-plan and https://docs.xendit.co/apidocs/update-subscription-plan-2
- Xendit webhook authentication and validation: https://docs.xendit.co/docs/integration-security
- Xendit cancellation endpoints: https://docs.xendit.co/apidocs/cancel-session and https://docs.xendit.co/apidocs/deactivate-subscription-plan-2

The app uses revocable opaque sessions rather than JWTs. Azure extraction is separate from receipt authentication. Xendit is selected only for Padala's optional subscription checkout; it does not provide bank-confirmation coverage and has not been connected to a live account in this repository.
