"""Render actual CLI output into a README GIF and a reduced-motion PNG.

This is a CLI output visualization, not a browser capture or UI mockup.
Run from the repository root with the normal app dependencies installed.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs/assets"
WIDTH, HEIGHT = 1200, 910
INK, GREEN, PAPER, MUTED = "#232D29", "#1B654B", "#FAF8F4", "#5C665F"
STEPS = [
    ("01 / Compare four sample resumes", ["scripts/demo_batch.py"], 4500),
    ("02 / Inspect exact source evidence",
     ["scripts/demo_evidence.py", "--candidate", "jordan", "--status", "supported"], 6500),
    ("03 / Inspect a requirement without evidence",
     ["scripts/demo_evidence.py", "--candidate", "ethan", "--status", "not_found"], 5000),
]


def font(size: int, *, serif: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (["C:/Windows/Fonts/georgia.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"]
                  if serif else ["C:/Windows/Fonts/consola.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"])
    for candidate in candidates:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default(size=size)


def render(title: str, command: str, output: str) -> Image.Image:
    frame = Image.new("RGB", (WIDTH, HEIGHT), PAPER)
    draw = ImageDraw.Draw(frame)
    draw.text((56, 34), "JobFit AI", font=font(42, serif=True), fill=INK)
    draw.text((56, 98), title, font=font(22), fill=GREEN)
    # The label remains visible on every frame, including when shared alone.
    draw.text((880, 52), "CLI DEMO OUTPUT", font=font(17), fill=MUTED)
    draw.line((56, 141, WIDTH - 56, 141), fill="#DCD9D0", width=1)
    command_font = font(17)
    if draw.textbbox((0, 0), command, font=command_font)[2] > WIDTH - 112:
        raise ValueError("Command exceeds the frame width")
    draw.text((56, 165), command, font=command_font, fill=GREEN)
    y = 214
    body_font = font(20)
    for line in output.splitlines():
        bounds = draw.textbbox((0, 0), line, font=body_font)
        if bounds[2] > WIDTH - 112 or y + 28 > HEIGHT - 78:
            raise ValueError(f"CLI output exceeds frame bounds: {line!r}")
        color = GREEN if line in {"REQUIREMENT", "RESULT", "RESUME EXCERPT", "SOURCE"} else INK
        draw.text((56, y), line, font=body_font, fill=color)
        y += 28
    draw.line((56, HEIGHT - 65, WIDTH - 56, HEIGHT - 65), fill="#DCD9D0", width=1)
    draw.text((56, HEIGHT - 44), "Fictional resumes / Local lexical analysis / Wording is not a hiring prediction",
              font=font(16), fill=MUTED)
    return frame


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ASSETS)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    frames, transcript = [], []
    for title, command_args, _ in STEPS:
        result = subprocess.run([sys.executable, *command_args], cwd=ROOT, check=True,
                                capture_output=True, text=True, encoding="utf-8",
                                env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        command = "$ python " + " ".join(command_args)
        frames.append(render(title, command, result.stdout))
        transcript.extend([title, command, result.stdout.rstrip(), ""])
    frames[1].save(args.output_dir / "demo-preview.png", optimize=True)
    indexed = [frame.convert("P", palette=Image.Palette.ADAPTIVE, colors=128) for frame in frames]
    indexed[0].save(args.output_dir / "demo-preview.gif", save_all=True, append_images=indexed[1:],
                    duration=[step[2] for step in STEPS], loop=0, disposal=2, optimize=True)
    (args.output_dir / "demo-output.txt").write_text("\n".join(transcript), encoding="utf-8")
    print("Created 3-frame CLI demo, static evidence preview, and text transcript.")


if __name__ == "__main__":
    main()
