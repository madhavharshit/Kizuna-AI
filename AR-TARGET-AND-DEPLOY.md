# AR target and free deployment

The AR page uses MindAR + A-Frame and demonstrates a browser-based camera overlay. It starts with the public MindAR sample target so you can test quickly. For your manufacturing-station marker:

1. Make or choose a high-detail printed image for the station (not a plain QR code; image tracking works best with visual features).
2. Open the official [MindAR Image Targets Compiler](https://hiukim.github.io/mind-ar-js-doc/tools/compile/).
3. Upload your JPG/PNG, click **Start**, wait until compilation finishes, then download `targets.mind`.
4. Put `targets.mind` in the `ar/` folder. In `ar/index.html`, change `imageTargetSrc` to `./targets.mind`. Replace the `target-card` image with the exact same marker file, so the printed image is the one being tracked.
5. Test the AR page on a phone over **HTTPS** or localhost. Mobile browsers generally require a secure context for camera access. Do not test by opening the HTML directly as a `file://` URL.

## Free hosting option

Deploy the static `ar/` directory to GitHub Pages or Vercel (free tiers; check the provider's current limits). Use the hosted HTTPS AR URL in `mobile/.env` as `EXPO_PUBLIC_AR_URL`. The phone app passes the approved procedure title, step and warning as URL parameters. The AR page is a demonstrator—not a certified industrial safety system.
