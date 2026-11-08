# Driver de navegador para visual-qa.mjs — Playwright (Python, ya está en
# el venv del repo con Chromium descargado; NO requiere dependencias npm).
#
# Uso:  python pw_driver.py <job.json>
# Lee un JSON con {url, viewport, timeoutMs, settleMs, scrollThrough,
# colorScheme, headed, screenshot, baseline, baselineTolerance,
# updateBaseline, audit{...}, auditSrc} y escribe UN JSON de resultado en
# stdout (el .mjs lo parsea; nada va a stderr salvo crash fatal).
#
# El screenshot se guarda en `screenshot`; si `baseline` existe se compara
# pixel a pixel (PIL, ya en el venv) y se reporta diffRatio/diffPixels.
# Si no existe baseline se crea copiando la captura actual (aviso, no falla)
# salvo que updateBaseline sea false y baseline sea null.

import json
import os
import shutil
import sys


def _result(**kw):
    base = {
        "ok": False,
        "finalUrl": "",
        "title": "",
        "consoleErrors": [],
        "pageErrors": [],
        "requestFailures": [],
        "audit": None,
        "screenshot": {"path": "", "bytes": 0, "baseline": "skipped", "diffRatio": None, "diffPixels": 0},
        "error": None,
    }
    base.update(kw)
    return base


def _diff_ratio(current, baseline):
    """Fracción de píxeles que cambian (cualquier canal > 12) entre dos PNG."""
    import numpy as np
    from PIL import Image, ImageChops

    a = Image.open(current).convert("RGB")
    b = Image.open(baseline).convert("RGB")
    if a.size != b.size:
        b = b.resize(a.size)
    diff = np.asarray(ImageChops.difference(a, b), dtype=np.uint8)
    changed = int((diff.max(axis=2) > 12).sum())
    return changed / float(diff.shape[0] * diff.shape[1]), changed


def run(job):
    from playwright.sync_api import sync_playwright

    url = job["url"]
    vp = job.get("viewport") or {"width": 1360, "height": 900}
    timeout_ms = int(job.get("timeoutMs") or 30000)
    settle_ms = int(job.get("settleMs") or 900)
    scroll_through = bool(job.get("scrollThrough", True))
    scheme = "dark" if job.get("colorScheme") == "dark" else "light"
    headed = bool(job.get("headed", False))
    shot_path = job.get("screenshot") or ""
    baseline_path = job.get("baseline") or ""
    tol = float(job.get("baselineTolerance", 0.02))
    update_baseline = bool(job.get("updateBaseline", False))

    console_errors = []
    page_errors = []
    req_failures = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=not headed,
            args=["--disable-gpu", "--disable-dev-shm-usage", "--force-color-profile=srgb"],
        )
        try:
            ctx = browser.new_context(
                viewport={"width": int(vp["width"]), "height": int(vp["height"])},
                device_scale_factor=1,
                color_scheme=scheme,
                reduced_motion="reduce",
            )
            page = ctx.new_page()
            page.set_default_timeout(timeout_ms)

            page.on(
                "console",
                lambda m: console_errors.append(m.text) if m.type == "error" else None,
            )
            page.on("pageerror", lambda e: page_errors.append(str(e)))
            page.on(
                "requestfailed",
                lambda r: req_failures.append(f"{r.method} {r.url} :: {r.failure}"),
            )

            page.goto(url, wait_until="load", timeout=timeout_ms)
            try:
                page.evaluate("() => document.fonts ? document.fonts.ready.then(() => true) : true")
            except Exception:
                pass

            if scroll_through:
                # Recorrer la página dispara IntersectionObserver/reveal y
                # carga perezosa; después se vuelve arriba para la captura.
                try:
                    page.evaluate(
                        """async () => {
                            const step = Math.max(400, Math.floor(window.innerHeight * 0.8));
                            const max = document.documentElement.scrollHeight;
                            for (let y = 0; y <= max; y += step) {
                                window.scrollTo(0, y);
                                await new Promise(r => setTimeout(r, 50));
                            }
                            window.scrollTo(0, 0);
                            await new Promise(r => setTimeout(r, 120));
                        }"""
                    )
                except Exception:
                    pass
            if settle_ms > 0:
                page.wait_for_timeout(settle_ms)

            audit_src = job.get("auditSrc") or ""
            audit_opts = job.get("audit") or {}
            audit = None
            if audit_src:
                expr = "(" + audit_src + ")(" + json.dumps(audit_opts) + ")"
                audit = page.evaluate(expr)

            if shot_path:
                os.makedirs(os.path.dirname(os.path.abspath(shot_path)), exist_ok=True)
                page.screenshot(path=shot_path, full_page=False)

            shot = {"path": shot_path, "bytes": os.path.getsize(shot_path) if shot_path and os.path.exists(shot_path) else 0,
                    "baseline": "skipped", "diffRatio": None, "diffPixels": 0}
            if shot_path and baseline_path:
                os.makedirs(os.path.dirname(os.path.abspath(baseline_path)), exist_ok=True)
                if update_baseline or not os.path.exists(baseline_path):
                    shutil.copyfile(shot_path, baseline_path)
                    shot["baseline"] = "updated" if update_baseline else "created"
                else:
                    try:
                        ratio, changed = _diff_ratio(shot_path, baseline_path)
                        shot["diffRatio"] = round(ratio, 5)
                        shot["diffPixels"] = changed
                        shot["baseline"] = "diff" if ratio > tol else "same"
                    except Exception as exc:
                        shot["baseline"] = "error"
                        shot["error"] = str(exc)

            final_url = page.url
            try:
                title = page.title()
            except Exception:
                title = ""
            ctx.close()
            browser.close()

            return _result(
                ok=True,
                finalUrl=final_url,
                title=title,
                consoleErrors=console_errors,
                pageErrors=page_errors,
                requestFailures=req_failures,
                audit=audit,
                screenshot=shot,
            )
        except Exception as exc:
            try:
                browser.close()
            except Exception:
                pass
            return _result(error=f"{type(exc).__name__}: {exc}", consoleErrors=console_errors,
                           pageErrors=page_errors, requestFailures=req_failures)


def main():
    # El resultado JSON puede traer nombres de producto con caracteres que la
    # consola cp1252 de Windows no codifica (✳ U+2733, etc.): forzar UTF-8 con
    # reemplazo para no morir en print() con UnicodeEncodeError.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if len(sys.argv) < 2:
        print(json.dumps(_result(error="falta el archivo de job")))
        return 2
    try:
        with open(sys.argv[1], "r", encoding="utf-8") as fh:
            job = json.load(fh)
    except Exception as exc:
        print(json.dumps(_result(error=f"job ilegible: {exc}")))
        return 2
    # El título se pide dentro del try de playwright; si falla el driver
    # entero, el .mjs ya tiene el error.
    out = run(job)
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
