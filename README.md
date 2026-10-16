# XBond Dashboard

Prebuilt XBond Dashboard for Clash-compatible controllers and sing-box.

- [Open dashboard](https://openxbond.github.io/dashboard/)
- [Download dashboard.zip](https://github.com/openxbond/dashboard/releases/latest/download/dashboard.zip)
- [Release history and checksums](https://github.com/openxbond/dashboard/releases)
- [Report an issue](https://github.com/openxbond/dashboard/issues)

Download `dashboard.zip` and `SHA256SUMS` from the same release. Run `sha256sum -c SHA256SUMS`, then extract into your controller's external UI directory or serve with a static web server. The ZIP has `index.html` at its root.

This repository contains compiled distributions and the tools needed to publish them. Application source is maintained privately. The `artifacts` branch holds release archives; `gh-pages` contains stable static files for CDN consumers. Release tags refer only to compiled artifacts.

Releases are published by `github-actions[bot]`. Git commits use `openxbond <noreply@xbond.net>`.

See [LICENSE](LICENSE) for the existing MIT license.
