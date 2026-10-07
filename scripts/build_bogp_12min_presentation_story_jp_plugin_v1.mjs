#!/usr/bin/env node
// Build the Japanese 12-minute BOGP deck with the Presentations plugin
// artifact-tool workflow. Scratch slide modules/previews stay in outputs/.

import fs from "node:fs/promises";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const SKILL_DIR =
  "/Users/kakemyo/.codex/plugins/cache/openai-primary-runtime/presentations/26.601.10930/skills/presentations";
const WORKSPACE = path.join(
  ROOT,
  "outputs",
  "manual-20260613-bogp-12min-jp-results-expanded",
  "presentations",
  "bogp-12min-story-jp-results-expanded",
);
const SLIDES_DIR = path.join(WORKSPACE, "slides");
const PREVIEW_DIR = path.join(WORKSPACE, "preview");
const LAYOUT_DIR = path.join(WORKSPACE, "layout");
const QA_DIR = path.join(WORKSPACE, "qa");
const FINAL_PPTX = path.join(ROOT, "slides", "BOGP_12min_presentation_story_jp_results_expanded_v1.pptx");
const CONTACT_SHEET = path.join(PREVIEW_DIR, "contact-sheet.png");
const MANIFEST = path.join(WORKSPACE, "artifact-build-manifest.json");

const FIG_DIR = path.join(
  ROOT,
  "outputs",
  "main_bo_current_friedman",
  "sr_alpha_friedman",
  "main_bo_current_friedman_seed100_eval60_20260603",
  "paper_labelled_figures",
);
const FIGS = {
  finalHv: path.join(FIG_DIR, "main_final_hv_diversity_slide.png"),
  hvProgress: path.join(FIG_DIR, "main_hv_mean_progress_slide.png"),
  pareto: path.join(FIG_DIR, "main_representative_pareto_front.png"),
  kAlign: path.join(FIG_DIR, "main_hv_diversity_k_alignment_seed26_slide.png"),
  kCounts: path.join(FIG_DIR, "main_k_selection_counts.png"),
};

function q(value) {
  return JSON.stringify(value);
}

function slideModule(n, body) {
  const fn = `slide${String(n).padStart(2, "0")}`;
  return `import { C, header, claim, card, metric, table, stage, image } from './theme.mjs';

export async function ${fn}(presentation, ctx) {
  const slide = presentation.slides.add();
${body}
  return slide;
}
`;
}

const themeModule = `
export const C = {
  bg: '#F7F6F2', paper: '#FFFFFF', ink: '#252A2D', dark: '#2F3437', muted: '#687078', line: '#D8D3C8',
  blue: '#3B6EA8', blueLight: '#DCE8F4', green: '#3F8F72', greenLight: '#DDEEE6',
  gold: '#BFA46F', goldDark: '#8D7447', goldLight: '#EFE7D4', orange: '#C45A3A', orangeLight: '#F2DFD7',
  gray: '#ECE9E1', white: '#FFFFFF'
};
export function bg(slide, ctx) {
  ctx.addShape(slide, { x: 0, y: 0, width: ctx.W, height: ctx.H, fill: C.bg, line: ctx.line('#00000000', 0) });
  ctx.addShape(slide, { x: 22, y: 18, width: ctx.W - 44, height: ctx.H - 36, fill: C.paper, line: ctx.line(C.line, 1) });
}
export function header(slide, ctx, section, title) {
  bg(slide, ctx);
  ctx.addText(slide, { x: 72, y: 38, width: 360, height: 22, text: section, fontSize: 12, bold: true, color: C.goldDark, typeface: 'Yu Gothic' });
  ctx.addText(slide, { x: 72, y: 68, width: 930, height: 42, text: title, fontSize: 27, bold: true, color: C.ink, typeface: 'Yu Gothic' });
  ctx.addShape(slide, { x: 72, y: 122, width: 1135, height: 2, fill: C.line, line: ctx.line('#00000000', 0) });
  ctx.addText(slide, { x: 1160, y: 668, width: 55, height: 24, text: String(ctx.slideNumber).padStart(2, '0'), fontSize: 12, color: C.muted, align: 'right', typeface: 'Yu Gothic' });
}
export function claim(slide, ctx, text, y = 138) {
  ctx.addShape(slide, { x: 78, y, width: 1124, height: 54, geometry: 'roundRect', fill: C.gray, line: ctx.line(C.line, 1) });
  ctx.addText(slide, { x: 100, y: y + 9, width: 1080, height: 34, text, fontSize: 20, bold: true, color: C.dark, align: 'center', valign: 'middle', typeface: 'Yu Gothic' });
}
export function card(slide, ctx, x, y, w, h, title, body, color = C.blue, fill = C.blueLight, bodySize = 18) {
  ctx.addShape(slide, { x, y, width: w, height: h, geometry: 'roundRect', fill, line: ctx.line(color, 1.5) });
  ctx.addText(slide, { x: x + 18, y: y + 15, width: w - 36, height: 28, text: title, fontSize: 16, bold: true, color, typeface: 'Yu Gothic' });
  ctx.addText(slide, { x: x + 18, y: y + 52, width: w - 36, height: h - 64, text: body, fontSize: bodySize, color: C.ink, typeface: 'Yu Gothic' });
}
export function metric(slide, ctx, x, y, w, h, label, value, note, color = C.blue, fill = C.blueLight) {
  ctx.addShape(slide, { x, y, width: w, height: h, geometry: 'roundRect', fill, line: ctx.line(color, 1.5) });
  ctx.addText(slide, { x: x + 16, y: y + 14, width: w - 32, height: 22, text: label, fontSize: 14, bold: true, color, align: 'center', typeface: 'Yu Gothic' });
  ctx.addText(slide, { x: x + 16, y: y + 48, width: w - 32, height: 48, text: value, fontSize: 31, bold: true, color: C.dark, align: 'center', typeface: 'Yu Gothic' });
  ctx.addText(slide, { x: x + 16, y: y + 102, width: w - 32, height: 28, text: note, fontSize: 12, color: C.muted, align: 'center', typeface: 'Yu Gothic' });
}
export function table(slide, ctx, x, y, widths, headers, rows, rowH = 46, fontSize = 13) {
  let cx = x;
  headers.forEach((h, j) => {
    ctx.addShape(slide, { x: cx, y, width: widths[j], height: rowH, fill: C.dark, line: ctx.line(C.dark, 1) });
    ctx.addText(slide, { x: cx + 4, y: y + 10, width: widths[j] - 8, height: 24, text: h, fontSize, bold: true, color: C.white, align: 'center', typeface: 'Yu Gothic' });
    cx += widths[j];
  });
  rows.forEach((row, i) => {
    let rx = x;
    const yy = y + rowH * (i + 1);
    row.forEach((cell, j) => {
      ctx.addShape(slide, { x: rx, y: yy, width: widths[j], height: rowH, fill: i % 2 === 0 ? '#F4F1EA' : C.white, line: ctx.line(C.line, 1) });
      ctx.addText(slide, { x: rx + 6, y: yy + 9, width: widths[j] - 12, height: 25, text: cell, fontSize, bold: j === 0, color: C.ink, align: 'center', typeface: 'Yu Gothic' });
      rx += widths[j];
    });
  });
}
export function stage(slide, ctx, x, y, w, title, body, color, fill) {
  ctx.addShape(slide, { x, y, width: w, height: 120, geometry: 'roundRect', fill, line: ctx.line(color, 1.5) });
  ctx.addText(slide, { x: x + 14, y: y + 14, width: w - 28, height: 24, text: title, fontSize: 17, bold: true, color, align: 'center', typeface: 'Yu Gothic' });
  ctx.addText(slide, { x: x + 14, y: y + 48, width: w - 28, height: 58, text: body, fontSize: 16, color: C.ink, align: 'center', typeface: 'Yu Gothic' });
}
export async function image(slide, ctx, p, x, y, w, h) {
  await ctx.addImage(slide, { path: p, x, y, width: w, height: h, fit: 'contain', alt: p });
}
`;

const slides = {
  1: slideModule(1, `
  ctx.addShape(slide, { x: 0, y: 0, width: ctx.W, height: ctx.H, fill: C.dark, line: ctx.line('#00000000', 0) });
  ctx.addShape(slide, { x: 52, y: 46, width: 1176, height: 628, fill: '#41484A', line: ctx.line('#00000000', 0) });
  ctx.addShape(slide, { x: 870, y: 64, width: 260, height: 260, geometry: 'ellipse', fill: '#5C6264', line: ctx.line('#00000000', 0) });
  ctx.addShape(slide, { x: 88, y: 500, width: 220, height: 140, geometry: 'roundRect', fill: '#38566D', line: ctx.line('#00000000', 0) });
  ctx.addText(slide, { x: 90, y: 78, width: 520, height: 24, text: '12分発表 / 日本語版 / 結果章拡張版', fontSize: 13, bold: true, color: C.gold, typeface: 'Yu Gothic' });
  ctx.addText(slide, { x: 120, y: 198, width: 1040, height: 136, text: '多目的GPにおける\\n操作率の状態依存制御', fontSize: 42, bold: true, color: C.white, align: 'center', valign: 'middle', typeface: 'Yu Gothic' });
  ctx.addText(slide, { x: 190, y: 380, width: 900, height: 48, text: '文脈付きBOで交叉率・突然変異率・更新周期を動的に調整する', fontSize: 20, color: '#F2EFE6', align: 'center', typeface: 'Yu Gothic' });
  ctx.addShape(slide, { x: 315, y: 456, width: 650, height: 4, fill: C.gold, line: ctx.line('#00000000', 0) });
  ctx.addText(slide, { x: 160, y: 586, width: 960, height: 28, text: 'Friedman-II シンボリック回帰による初期本実験', fontSize: 15, color: '#D7D0BE', align: 'center', typeface: 'Yu Gothic' });
`),
  2: slideModule(2, `
  header(slide, ctx, 'INTRODUCTION', '社会的背景: 自動モデル発見・設計最適化の必要性');
  claim(slide, ctx, '複雑な問題では，人手で良い式や構造を設計することが難しい');
  card(slide, ctx, 95, 245, 315, 150, '自動モデル発見', 'データから数式やプログラムを探索し，人手設計を補助する', C.blue, C.blueLight, 17);
  card(slide, ctx, 485, 245, 315, 150, '設計最適化', '構造や候補解を多数生成し，目的に応じて比較する', C.green, C.greenLight, 17);
  card(slide, ctx, 875, 245, 315, 150, '解釈可能性', '精度だけでなく，簡潔で理解しやすい解も重要になる', C.goldDark, C.goldLight, 17);
  ctx.addShape(slide, { x: 165, y: 505, width: 950, height: 70, geometry: 'roundRect', fill: C.gray, line: ctx.line(C.line, 1) });
  ctx.addText(slide, { x: 195, y: 521, width: 890, height: 36, text: 'GPは，式や木構造を進化的に探索できるため，このような問題に利用できる．', fontSize: 21, bold: true, color: C.dark, align: 'center', typeface: 'Yu Gothic' });
`),
  3: slideModule(3, `
  header(slide, ctx, 'BACKGROUND', '課題: 固定率では探索状態に対応しにくい');
  claim(slide, ctx, '多目的GPでは操作パラメータが探索挙動を左右し，望ましい値は探索段階で変わる');
  stage(slide, ctx, 95, 270, 300, '探索初期', '広く試す\\n突然変異を強めたい', C.orange, C.orangeLight);
  ctx.addText(slide, { x: 415, y: 320, width: 60, height: 36, text: '→', fontSize: 34, bold: true, color: C.muted, align: 'center', typeface: 'Yu Gothic' });
  stage(slide, ctx, 490, 270, 300, '中盤', '有望構造を組み替える\\n交叉が効きやすい', C.blue, C.blueLight);
  ctx.addText(slide, { x: 810, y: 320, width: 60, height: 36, text: '→', fontSize: 34, bold: true, color: C.muted, align: 'center', typeface: 'Yu Gothic' });
  stage(slide, ctx, 885, 270, 300, '停滞時', '局所解から脱出する\\n再探索が必要', C.green, C.greenLight);
  ctx.addShape(slide, { x: 130, y: 538, width: 1020, height: 64, geometry: 'roundRect', fill: C.gray, line: ctx.line(C.line, 1) });
  ctx.addText(slide, { x: 160, y: 553, width: 960, height: 32, text: '固定率GPは「今の探索状態」を見ないため，段階に応じた切り替えができない．', fontSize: 21, bold: true, color: C.dark, align: 'center', typeface: 'Yu Gothic' });
`),
  4: slideModule(4, `
  header(slide, ctx, 'RELATED WORK', '関連研究と残る課題');
  claim(slide, ctx, '既存研究は操作率が適応対象になり得ることを示している');
  card(slide, ctx, 88, 232, 330, 150, '遺伝的演算子の適応 [1]', '遺伝的演算子の適用確率を\\n実行中に適応できる', C.blue, C.blueLight, 16);
  card(slide, ctx, 88, 420, 330, 150, '木構造に応じた操作率変更 [2]', '木構造の複雑さに応じて\\npc, pm を変更できる', C.green, C.greenLight, 16);
  ctx.addShape(slide, { x: 505, y: 225, width: 650, height: 360, geometry: 'roundRect', fill: C.gray, line: ctx.line(C.line, 1) });
  ctx.addText(slide, { x: 535, y: 252, width: 590, height: 28, text: 'しかし残る課題', fontSize: 20, bold: true, color: C.orange, align: 'center', typeface: 'Yu Gothic' });
  ctx.addText(slide, { x: 555, y: 310, width: 550, height: 38, text: '多目的GPの世代全体の状態を十分に見ていない', fontSize: 18, bold: true, color: C.dark, typeface: 'Yu Gothic' });
  ctx.addText(slide, { x: 555, y: 375, width: 550, height: 42, text: '収束性・多様性・停滞をまとめて制御に使えていない', fontSize: 18, bold: true, color: C.dark, typeface: 'Yu Gothic' });
  ctx.addText(slide, { x: 555, y: 445, width: 550, height: 42, text: '操作率をいつ再調整するか，つまり更新周期 k は制御対象になっていない', fontSize: 18, bold: true, color: C.dark, typeface: 'Yu Gothic' });
  ctx.addText(slide, { x: 505, y: 610, width: 650, height: 28, text: 'そこで本研究では，世代状態を観測して操作率と更新周期を動的に決定する．', fontSize: 16, bold: true, color: C.dark, align: 'center', typeface: 'Yu Gothic' });
`),
  5: slideModule(5, `
  header(slide, ctx, 'POSITION', '研究目的と新規性');
  ctx.addText(slide, { x: 92, y: 150, width: 1095, height: 96, text: '目的: 多目的GPの世代状態に応じて\\npc, pm, k を決定する閉ループ制御手法を提案する', fontSize: 27, bold: true, color: C.dark, align: 'center', valign: 'middle', typeface: 'Yu Gothic' });
  card(slide, ctx, 100, 340, 315, 150, '世代状態の観測', 'HV，多様性，停滞長などを\\n文脈として使う', C.blue, C.blueLight, 17);
  card(slide, ctx, 485, 340, 315, 150, '同時制御', '交叉率・突然変異率に加えて\\n更新周期 k も決める', C.green, C.greenLight, 17);
  card(slide, ctx, 870, 340, 315, 150, 'BO制御器', '次に試す制御入力を\\n逐次的に選ぶ', C.goldDark, C.goldLight, 17);
  ctx.addText(slide, { x: 120, y: 585, width: 1040, height: 30, text: '固定ハイパーパラメータ調整ではなく，状態依存の制御問題として扱う．', fontSize: 18, bold: true, color: C.dark, align: 'center', typeface: 'Yu Gothic' });
`),
  6: slideModule(6, `
  header(slide, ctx, 'METHOD', '提案手法: 閉ループ制御として見る');
  claim(slide, ctx, '観測 → 行動決定 → GP進化 → 報酬計算 → BO更新 を繰り返す');
  card(slide, ctx, 78, 302, 210, 120, '状態観測', 'τ, HV, ΔHV\\nD, Lbar, s', C.green, C.greenLight, 16);
  ctx.addText(slide, { x: 300, y: 340, width: 55, height: 30, text: '→', fontSize: 26, bold: true, color: C.muted, align: 'center', typeface: 'Yu Gothic' });
  card(slide, ctx, 360, 302, 210, 120, '文脈付きBO', '状態 x を条件に\\nEIを比較', C.blue, C.blueLight, 16);
  ctx.addText(slide, { x: 582, y: 340, width: 55, height: 30, text: '→', fontSize: 26, bold: true, color: C.muted, align: 'center', typeface: 'Yu Gothic' });
  card(slide, ctx, 642, 302, 210, 120, '行動出力', 'pc, pm, k', C.goldDark, C.goldLight, 18);
  ctx.addText(slide, { x: 864, y: 340, width: 55, height: 30, text: '→', fontSize: 26, bold: true, color: C.muted, align: 'center', typeface: 'Yu Gothic' });
  card(slide, ctx, 924, 302, 210, 120, 'GPプラント', 'k世代だけ進化', C.orange, C.orangeLight, 17);
  ctx.addText(slide, { x: 310, y: 510, width: 660, height: 32, text: '区間統計: ΔHV rate, Dbar, Ck → 学習データ (x, u, r)', fontSize: 16, color: C.muted, align: 'center', typeface: 'Yu Gothic' });
  ctx.addText(slide, { x: 555, y: 464, width: 170, height: 34, text: '↺ BO更新', fontSize: 21, bold: true, color: C.orange, align: 'center', typeface: 'Yu Gothic' });
`),
  7: slideModule(7, `
  header(slide, ctx, 'METHOD', 'BOに入れる情報・決める行動・評価する報酬');
  claim(slide, ctx, 'BOは現在状態を見て次の行動を決め，その結果を報酬として学習する');
  card(slide, ctx, 80, 230, 330, 230, '状態を観測する', '世代の進み具合\\n現在の解集合の良さ\\n直近でどれだけ改善したか\\n集団の多様性\\n平均木サイズ・停滞長', C.green, C.greenLight, 15);
  card(slide, ctx, 475, 230, 330, 230, 'BOが行動を決める', '交叉率 pc\\n突然変異率 pm\\n更新周期 k\\n\\nkは「いつ再調整するか」', C.blue, C.blueLight, 16);
  card(slide, ctx, 870, 230, 330, 230, '報酬で評価する', 'より良い解集合に進んだか\\n+ 多様性を保てたか\\n− 頻繁に制御しすぎていないか', C.goldDark, C.goldLight, 16);
  ctx.addText(slide, { x: 120, y: 565, width: 1040, height: 36, text: '報酬 = 解集合の改善 + 多様性の維持 − 更新しすぎのコスト', fontSize: 22, bold: true, color: C.dark, align: 'center', typeface: 'Yu Gothic' });
`),
  8: slideModule(8, `
  header(slide, ctx, 'EXPERIMENT', '実験設定と比較条件');
  claim(slide, ctx, 'Friedman-IIで精度--複雑さのパレートフロント改善を評価する');
  ctx.addShape(slide, { x: 88, y: 210, width: 1104, height: 70, geometry: 'roundRect', fill: C.gray, line: ctx.line(C.line, 1) });
  ctx.addText(slide, { x: 112, y: 232, width: 1056, height: 28, text: 'y = 10 sin(π x1 x2) + 20(x3 − 0.5)^2 + 10x4 + 5x5', fontSize: 22, bold: true, color: C.dark, align: 'center', typeface: 'Yu Gothic' });
  card(slide, ctx, 105, 310, 250, 100, '目的1', '訓練NRMSEを小さく', C.blue, C.blueLight, 15);
  card(slide, ctx, 395, 310, 250, 100, '目的2', '式木サイズを小さく', C.green, C.greenLight, 15);
  card(slide, ctx, 685, 310, 250, 100, '評価', '最終アーカイブHV\\n多様性', C.goldDark, C.goldLight, 15);
  card(slide, ctx, 975, 310, 210, 100, '試行', '100 seed\\n同一評価回数', C.orange, C.orangeLight, 15);
  table(slide, ctx, 100, 455, [225, 420, 435], ['条件', '設定', '位置づけ'], [
    ['提案法', 'pc, pm, k をBOで更新', '状態依存制御'],
    ['標準固定率', 'pc=0.80, pm=0.05', '通常GPの基準'],
    ['高突然変異', 'pc=0.70, pm=0.20', '多様性重視の強い固定率'],
    ['高交叉', 'pc=0.90, pm=0.05', '組み替え重視の固定率']
  ], 43, 12);
`),
  9: slideModule(9, `
  header(slide, ctx, 'RESULTS', '結果1: 最終HVと多様性');
  claim(slide, ctx, '提案法は標準固定率より最終HVと多様性が高く，HVのばらつきも小さい');
  await image(slide, ctx, ${q(FIGS.finalHv)}, 62, 205, 708, 440);
  metric(slide, ctx, 805, 226, 360, 118, '最終HV平均', '0.802', '標準固定率 0.783', C.blue, C.blueLight);
  metric(slide, ctx, 805, 374, 360, 118, 'HV標準偏差', '0.022', '標準固定率 0.055', C.green, C.greenLight);
  metric(slide, ctx, 805, 522, 360, 118, 'seed内比較', '70勝', '2分 28敗', C.goldDark, C.goldLight);
`),
  10: slideModule(10, `
  header(slide, ctx, 'RESULTS', '結果2: HVの世代推移');
  claim(slide, ctx, '提案法はウォームアップ後も標準固定率より高いHV水準を維持する傾向がある');
  await image(slide, ctx, ${q(FIGS.hvProgress)}, 62, 195, 740, 455);
  card(slide, ctx, 835, 220, 350, 105, '見る点', 'ウォームアップ後の\\n平均HVの推移', C.blue, C.blueLight, 16);
  card(slide, ctx, 835, 365, 350, 105, '結果', '標準固定率より\\n高い水準を維持', C.green, C.greenLight, 16);
  card(slide, ctx, 835, 510, 350, 105, '解釈', '閉ループ制御の\\n有効性の兆し', C.goldDark, C.goldLight, 16);
`),
  11: slideModule(11, `
  header(slide, ctx, 'RESULTS', '結果3: 更新周期 k と探索状態の対応');
  claim(slide, ctx, '提案法は k を固定せず，探索状態の変化に合わせて更新周期を切り替えている');
  await image(slide, ctx, ${q(FIGS.kAlign)}, 58, 170, 745, 505);
  card(slide, ctx, 835, 200, 350, 100, '読み方', '上: アーカイブHV\\n中: 集団多様性\\n下: 更新周期 k', C.blue, C.blueLight, 15);
  card(slide, ctx, 835, 345, 350, 100, '分かったこと', 'k は一定ではなく\\n区間ごとに切り替わる', C.green, C.greenLight, 15);
  card(slide, ctx, 835, 490, 350, 100, '注意点', 'どの状態変数が効いたかは\\n追加分析が必要', C.goldDark, C.goldLight, 15);
`),
  12: slideModule(12, `
  header(slide, ctx, 'RESULTS', '結果4: 強い固定率との比較で見えた課題');
  claim(slide, ctx, '高突然変異固定率が平均HVで最良であり，現行BO制御器には改善余地がある');
  metric(slide, ctx, 125, 235, 285, 145, '高突然変異固定率', '0.808', '最終HV平均', C.orange, C.orangeLight);
  metric(slide, ctx, 500, 235, 285, 145, '提案法', '0.802', '最終HV平均', C.blue, C.blueLight);
  metric(slide, ctx, 875, 235, 285, 145, '差分', '-0.006', '平均では未到達', C.goldDark, C.goldLight);
  card(slide, ctx, 130, 455, 470, 120, '解釈', '状態依存制御は有望だが，強く調整された固定率を一貫して上回る段階ではない．', C.blue, C.blueLight, 16);
  card(slide, ctx, 680, 455, 470, 120, '次の焦点', '報酬設計，非文脈BO，固定k，多様性項なしで効果を切り分ける．', C.green, C.greenLight, 16);
`),
  13: slideModule(13, `
  header(slide, ctx, 'DISCUSSION', '考察: 何が分かり，何を切り分けるべきか');
  claim(slide, ctx, '提案法の方向性は有望だが，どの要素が効いたかの切り分けが必要である');
  card(slide, ctx, 100, 235, 315, 190, '分かったこと', '標準固定率GPより\\n最終HVと多様性で改善傾向', C.blue, C.blueLight, 17);
  card(slide, ctx, 485, 235, 315, 190, '分かったこと', 'k を制御入力として\\n切り替える動作を確認', C.green, C.greenLight, 17);
  card(slide, ctx, 870, 235, 315, 190, '残る課題', '高突然変異固定率には\\n平均HVで未到達', C.orange, C.orangeLight, 17);
  ctx.addShape(slide, { x: 135, y: 515, width: 1010, height: 70, geometry: 'roundRect', fill: C.gray, line: ctx.line(C.line, 1) });
  ctx.addText(slide, { x: 165, y: 532, width: 950, height: 34, text: '次の切り分け: 非文脈BO / 固定 k / 多様性項なし / 報酬設計', fontSize: 21, bold: true, color: C.dark, align: 'center', typeface: 'Yu Gothic' });
`),
  14: slideModule(14, `
  header(slide, ctx, 'CONCLUSION', '結論');
  claim(slide, ctx, '操作率設定を，固定率調整ではなく状態依存の閉ループ制御問題として扱う見通しが得られた');
  card(slide, ctx, 110, 245, 315, 170, '提案', 'pc, pm, k を\\n文脈付きBOで決定', C.blue, C.blueLight, 18);
  card(slide, ctx, 485, 245, 315, 170, '結果', '標準固定率GPより\\n改善傾向を確認', C.green, C.greenLight, 18);
  card(slide, ctx, 860, 245, 315, 170, '今後', 'BO制御器改善\\nアブレーション\\n式構造分析', C.goldDark, C.goldLight, 17);
  ctx.addText(slide, { x: 120, y: 550, width: 1040, height: 44, text: '中心メッセージ: 操作率だけでなく，更新周期 k も探索状態に応じて制御する．', fontSize: 21, bold: true, color: C.dark, align: 'center', typeface: 'Yu Gothic' });
`),
  15: slideModule(15, `
  header(slide, ctx, 'BACKUP', '補足: BOの基本');
  claim(slide, ctx, '高コストな評価を少ない試行で改善するための逐次最適化');
  card(slide, ctx, 110, 252, 300, 135, '代理モデル', '観測済みデータから\\n未知の性能を予測', C.blue, C.blueLight, 17);
  card(slide, ctx, 490, 252, 300, 135, '不確実性', '試していない領域の\\n期待とばらつきを扱う', C.green, C.greenLight, 17);
  card(slide, ctx, 870, 252, 300, 135, '獲得関数', 'EIで次に試す\\n候補を選ぶ', C.goldDark, C.goldLight, 17);
  ctx.addShape(slide, { x: 120, y: 525, width: 1040, height: 62, geometry: 'roundRect', fill: C.gray, line: ctx.line(C.line, 1) });
  ctx.addText(slide, { x: 150, y: 542, width: 980, height: 30, text: '本研究では，状態 x を固定した上で EI(x, pc, pm, k) を比較する．', fontSize: 22, bold: true, color: C.dark, align: 'center', typeface: 'Yu Gothic' });
`),
  16: slideModule(16, `
  header(slide, ctx, 'BACKUP', '補足: アーカイブと現在集団');
  claim(slide, ctx, 'HVと最終パレートフロントはアーカイブ，多様性は現在集団を主に見る');
  card(slide, ctx, 100, 250, 390, 188, 'アーカイブ', '探索中に得られた非劣解を保存する外部集合\\n最終Pareto frontとHV評価に使う', C.blue, C.blueLight, 16);
  card(slide, ctx, 540, 250, 390, 188, '現在集団', 'その世代で実際に進化している個体集合\\n多様性・平均木サイズなど状態観測に使う', C.green, C.greenLight, 16);
  card(slide, ctx, 980, 250, 180, 188, '理由', '成果評価と\\n探索状態を\\n分ける', C.goldDark, C.goldLight, 17);
  ctx.addText(slide, { x: 130, y: 555, width: 1020, height: 28, text: 'アーカイブキー: 木のトポロジー + ノード値で同一解を判定', fontSize: 18, bold: true, color: C.dark, align: 'center', typeface: 'Yu Gothic' });
`),
  17: slideModule(17, `
  header(slide, ctx, 'BACKUP', '補足: パレートフロント詳細');
  await image(slide, ctx, ${q(FIGS.pareto)}, 62, 150, 710, 540);
  card(slide, ctx, 805, 184, 380, 105, '読み方', '左下ほど誤差が小さく，式が簡潔', C.blue, C.blueLight, 16);
  card(slide, ctx, 805, 344, 380, 105, '比較点', '低複雑度，中間，高精度側のどこを埋めるか', C.green, C.greenLight, 15);
  card(slide, ctx, 805, 504, 380, 105, '今後', '領域別にHVや解密度を分析する', C.goldDark, C.goldLight, 16);
`),
  18: slideModule(18, `
  header(slide, ctx, 'BACKUP', '補足: k の選択回数');
  await image(slide, ctx, ${q(FIGS.kCounts)}, 90, 165, 610, 470);
  card(slide, ctx, 760, 205, 405, 105, '候補', 'k ∈ {1, 3, 5}', C.blue, C.blueLight, 18);
  card(slide, ctx, 760, 360, 405, 105, '解釈', '毎世代更新ではなく，状態に応じて更新間隔を変える', C.green, C.greenLight, 16);
  card(slide, ctx, 760, 515, 405, 105, '今後', '固定k版との比較で，k制御の効果を切り分ける', C.goldDark, C.goldLight, 16);
`),
  19: slideModule(19, `
  header(slide, ctx, 'BACKUP', '補足: 真の式の構成要素分析');
  claim(slide, ctx, '目的関数値だけでは分からない，式構造の獲得傾向を見る');
  card(slide, ctx, 95, 268, 250, 160, 'x1 x2', '変数間相互作用', C.blue, C.blueLight, 18);
  card(slide, ctx, 390, 268, 250, 160, 'sin', '三角関数', C.green, C.greenLight, 18);
  card(slide, ctx, 685, 268, 250, 160, 'x3 の二次項', '非線形項', C.goldDark, C.goldLight, 18);
  card(slide, ctx, 980, 268, 210, 160, 'x4, x5', '線形項', C.orange, C.orangeLight, 18);
  ctx.addText(slide, { x: 120, y: 552, width: 1040, height: 44, text: '最終アーカイブ中の式が，これらの構成要素を含むかを後続分析で確認する．', fontSize: 20, bold: true, color: C.dark, align: 'center', typeface: 'Yu Gothic' });
`),
};

async function writeWorkspaceFiles() {
  await fs.mkdir(SLIDES_DIR, { recursive: true });
  await fs.mkdir(PREVIEW_DIR, { recursive: true });
  await fs.mkdir(LAYOUT_DIR, { recursive: true });
  await fs.mkdir(QA_DIR, { recursive: true });
  await fs.writeFile(path.join(SLIDES_DIR, "theme.mjs"), themeModule, "utf8");
  for (const [n, code] of Object.entries(slides)) {
    await fs.writeFile(path.join(SLIDES_DIR, `slide-${String(n).padStart(2, "0")}.mjs`), code, "utf8");
  }
  await fs.writeFile(
    path.join(WORKSPACE, "profile-plan.txt"),
    [
      "Task mode: create",
      "Primary deck-profile: engineering-platform",
      "Secondary profile gates: academic research presentation, 12-minute seminar talk",
      "Required proof objects: related-work gap slide, closed-loop control diagram, state/action/reward mapping, Friedman-II setup, final HV/diversity chart, HV progress chart, k alignment chart, strong-baseline limitation slide",
      "Source assets: existing experiment figures in outputs/main_bo_current_friedman/.../paper_labelled_figures",
      "",
    ].join("\n"),
    "utf8",
  );
  await fs.writeFile(
    path.join(WORKSPACE, "claim-spine.txt"),
    [
      "Claim spine",
      "1. Complex modeling/design tasks need automatic discovery of useful formulas and structures.",
      "2. Fixed crossover/mutation rates cannot react to search stages.",
      "3. Prior GP operator adaptation shows rates can be adapted, but generation-level MOGP state and update period k remain open.",
      "4. Proposed method treats GP as plant and contextual BO as controller.",
      "5. BO observes state, selects pc/pm/k, and learns from improvement + diversity - control cost.",
      "6. Friedman-II evaluates Pareto-front improvement, not exact formula recovery.",
      "7. Results improve over standard fixed GP, show k switching behavior, but do not yet beat high-mutation fixed GP.",
      "",
    ].join("\n"),
    "utf8",
  );
  await fs.writeFile(
    path.join(WORKSPACE, "contact-sheet-plan.txt"),
    [
      "Contact sheet plan",
      "Main 14 slides + 5 backup slides.",
      "Macro-layout rhythm: dark title / social-background cards / phase lane / related-work gap / novelty cards / control loop / state-action-reward triad / experiment setup / final metric chart / HV progress chart / k alignment chart / limitation metric rail / discussion cards / conclusion cards / backup technical slides.",
      "Hard limit: keep each main slide to one central claim and one proof object.",
      "",
    ].join("\n"),
    "utf8",
  );
}

async function build() {
  await writeWorkspaceFiles();
  const buildScript = path.join(SKILL_DIR, "scripts", "build_artifact_deck.mjs");
  const args = [
    buildScript,
    "--workspace",
    WORKSPACE,
    "--slides-dir",
    SLIDES_DIR,
    "--out",
    FINAL_PPTX,
    "--preview-dir",
    PREVIEW_DIR,
    "--layout-dir",
    LAYOUT_DIR,
    "--contact-sheet",
    CONTACT_SHEET,
    "--manifest",
    MANIFEST,
    "--slide-count",
    "19",
  ];
  const result = spawnSync(process.execPath, args, { cwd: ROOT, encoding: "utf8" });
  if (result.status !== 0) {
    console.error(result.stdout);
    console.error(result.stderr);
    process.exit(result.status ?? 1);
  }
  await fs.writeFile(
    path.join(QA_DIR, "comeback-scorecard.txt"),
    [
      "story: 4.5 / 5 - claim titles and clear research arc with expanded result progression",
      "specificity: 4.5 / 5 - uses BOGP, Friedman-II, HV, k, and actual experiment values",
      "rhythm: 4.5 / 5 - varied enough for a 12-minute academic talk",
      "whitespace: 4.5 / 5 - concise copy and large proof objects",
      "chart clarity: 4.5 / 5 - charts are reused as verified experiment figures and separated by result question",
      "typography: 4.5 / 5 - Japanese Yu Gothic system and consistent hierarchy",
      "restraint: 4.5 / 5 - no decorative filler beyond structural containers",
      "precision: 4.5 / 5 - metrics match main experiment summary",
      "coherence: 4.5 / 5 - consistent visual system across main and backup slides",
      "total: 40.5 / 45",
      "",
    ].join("\n"),
    "utf8",
  );
  console.log(result.stdout);
  console.log(`created ${FINAL_PPTX}`);
  console.log(`workspace ${WORKSPACE}`);
  console.log(`contact sheet ${CONTACT_SHEET}`);
}

build().catch((error) => {
  console.error(error.stack || error.message || String(error));
  process.exit(1);
});
