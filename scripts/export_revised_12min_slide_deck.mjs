import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  Presentation,
  PresentationFile,
} from "/Users/kakemyo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const root = path.resolve(__dirname, "..");

const imageDir = path.join(root, "slides", "revised_12min_slide_images");
const previewDir = path.join(root, "slides", "revised_12min_slide_deck_preview");
const outputPptx = path.join(root, "slides", "revised_12min_slide_deck.pptx");
const montagePath = path.join(previewDir, "deck-montage.webp");

const slideFiles = [
  "01_title.png",
  "02_social_background.png",
  "03_fixed_rate_problem.png",
  "04_related_work_gap.png",
  "05_objective_novelty.png",
  "06_closed_loop_method.png",
  "07_state_action.png",
  "08_reward_design.png",
  "09_experiment_setup.png",
  "10_result_standard_fixed.png",
  "11_result_strong_fixed.png",
  "12_result_k_behavior.png",
  "13_discussion.png",
  "14_conclusion.png",
  "B01_bo_basics.png",
  "B02_archive_vs_population.png",
  "B03_pareto_front_detail.png",
  "B05_k_selection_counts.png",
  "B06_true_formula_components.png",
];

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

async function readImageBlob(filePath) {
  const bytes = await fs.readFile(filePath);
  return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
}

async function main() {
  await fs.mkdir(previewDir, { recursive: true });

  const presentation = Presentation.create({
    slideSize: { width: 1920, height: 1080 },
  });

  for (const [index, fileName] of slideFiles.entries()) {
    const imagePath = path.join(imageDir, fileName);
    await fs.access(imagePath);

    const slide = presentation.slides.add();
    slide.background.fill = "#FFFFFF";
    slide.images.add({
      blob: await readImageBlob(imagePath),
      contentType: "image/png",
      alt: fileName.replace(".png", ""),
      fit: "cover",
      position: { left: 0, top: 0, width: 1920, height: 1080 },
    });

    const stem = `slide-${String(index + 1).padStart(2, "0")}`;
    await writeBlob(
      path.join(previewDir, `${stem}.png`),
      await presentation.export({ slide, format: "png", scale: 0.5 }),
    );
    await fs.writeFile(
      path.join(previewDir, `${stem}.layout.json`),
      await (await slide.export({ format: "layout" })).text(),
    );
  }

  await writeBlob(
    montagePath,
    await presentation.export({ format: "webp", montage: true, scale: 0.35 }),
  );

  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(outputPptx);

  console.log(JSON.stringify({ outputPptx, previewDir, montagePath, slideCount: slideFiles.length }, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
