# SouthPlate

SouthPlate is a static website built with HTML, JavaScript, and image assets.

## Run locally

From the project directory, start a local web server:

```bash
python -m http.server 8000
```

Then visit:

```text
http://localhost:8000/SouthPlate.dc.html
```

## Project structure

- `SouthPlate.dc.html` — main website page
- `support.js` — client-side behavior
- `uploads/` — website image assets
- `vercel.json` — maps the site root to the main page on Vercel

## Deploy

The project is configured for deployment as a static site on Vercel. The root URL is rewritten to `SouthPlate.dc.html`.
