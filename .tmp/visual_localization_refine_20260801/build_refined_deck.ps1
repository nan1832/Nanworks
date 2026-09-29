$ErrorActionPreference = 'Stop'

$root = 'D:\开题\正式开题\Model Edit\bli2-reasonvqa\dataset'
$refDir = Join-Path $root '.tmp\visual_localization_refine_20260801\reference_render'
$hero = Join-Path $root '.tmp\visual_localization_refine_20260801\assets\vlm_kg_editing_hero.png'
$outDir = Join-Path $root 'outputs'
$out = Join-Path $outDir '视觉编辑层定位_方法讲解与后续工作_精修版.pptx'
$renderDir = Join-Path $root '.tmp\visual_localization_refine_20260801\final_render'
New-Item -ItemType Directory -Force -Path $outDir,$renderDir | Out-Null
if (Test-Path $out) { Remove-Item -LiteralPath $out -Force }

function RGB([int]$r,[int]$g,[int]$b) { return $r + 256*$g + 65536*$b }
$C = @{
  Ink=RGB 31 42 55; Muted=RGB 91 103 116; Light=RGB 246 248 252; Line=RGB 218 226 236
  Teal=RGB 169 233 228; TealDark=RGB 22 142 136; Blue=RGB 55 113 229; BlueLight=RGB 231 239 255
  Violet=RGB 118 82 210; VioletLight=RGB 241 236 255; Orange=RGB 238 143 52; OrangeLight=RGB 255 242 223
  Green=RGB 54 160 112; GreenLight=RGB 231 248 239; Red=RGB 215 73 73; RedLight=RGB 255 235 235
  White=RGB 255 255 255; Dark=RGB 13 38 62; Gray=RGB 150 160 171; Yellow=RGB 248 197 70
}

$pp = New-Object -ComObject PowerPoint.Application
$pp.Visible = -1
$pres = $pp.Presentations.Add()
$pres.PageSetup.SlideWidth = 960
$pres.PageSetup.SlideHeight = 540

function Add-Text($s,[string]$txt,[double]$x,[double]$y,[double]$w,[double]$h,[double]$size=18,[int]$color=$C.Ink,[string]$font='Microsoft YaHei',[int]$bold=0,[int]$align=1) {
  $sh=$s.Shapes.AddTextbox(1,$x,$y,$w,$h)
  $sh.TextFrame.MarginLeft=0; $sh.TextFrame.MarginRight=0; $sh.TextFrame.MarginTop=0; $sh.TextFrame.MarginBottom=0
  $sh.TextFrame.WordWrap=-1
  $tr=$sh.TextFrame.TextRange; $tr.Text=$txt; $tr.Font.Name=$font; $tr.Font.NameFarEast=$font; $tr.Font.Size=$size; $tr.Font.Color.RGB=$color; $tr.Font.Bold=$bold; $tr.ParagraphFormat.Alignment=$align
  return $sh
}
function Add-Box($s,[string]$txt,[double]$x,[double]$y,[double]$w,[double]$h,[int]$fill=$C.White,[int]$line=$C.Line,[double]$size=16,[int]$color=$C.Ink,[double]$radius=0,[int]$bold=0,[int]$align=2) {
  $type=5
  $sh=$s.Shapes.AddShape($type,$x,$y,$w,$h)
  $sh.Fill.ForeColor.RGB=$fill; $sh.Line.ForeColor.RGB=$line; $sh.Line.Weight=1.25
  $sh.TextFrame.MarginLeft=8; $sh.TextFrame.MarginRight=8; $sh.TextFrame.MarginTop=5; $sh.TextFrame.MarginBottom=5
  $sh.TextFrame.VerticalAnchor=3; $sh.TextFrame.WordWrap=-1
  $tr=$sh.TextFrame.TextRange; $tr.Text=$txt; $tr.Font.Name='Microsoft YaHei'; $tr.Font.NameFarEast='Microsoft YaHei'; $tr.Font.Size=$size; $tr.Font.Color.RGB=$color; $tr.Font.Bold=$bold; $tr.ParagraphFormat.Alignment=$align
  return $sh
}
function Add-Line($s,[double]$x1,[double]$y1,[double]$x2,[double]$y2,[int]$color=$C.Gray,[double]$weight=1.5,[switch]$arrow) {
  $ln=$s.Shapes.AddLine($x1,$y1,$x2,$y2); $ln.Line.ForeColor.RGB=$color; $ln.Line.Weight=$weight
  if($arrow){$ln.Line.EndArrowheadStyle=3}
  return $ln
}
function Add-Circle($s,[string]$txt,[double]$x,[double]$y,[double]$d,[int]$fill,[int]$color=$C.White,[double]$size=18) {
  $sh=$s.Shapes.AddShape(9,$x,$y,$d,$d); $sh.Fill.ForeColor.RGB=$fill; $sh.Line.Visible=0
  $sh.TextFrame.VerticalAnchor=3; $sh.TextFrame.MarginLeft=2; $sh.TextFrame.MarginRight=2; $sh.TextFrame.MarginTop=2; $sh.TextFrame.MarginBottom=2
  $tr=$sh.TextFrame.TextRange; $tr.Text=$txt; $tr.Font.Name='Microsoft YaHei'; $tr.Font.NameFarEast='Microsoft YaHei'; $tr.Font.Size=$size; $tr.Font.Bold=-1; $tr.Font.Color.RGB=$color; $tr.ParagraphFormat.Alignment=2
  return $sh
}
function Add-Title($s,[string]$title,[string]$kicker='') {
  if($kicker){ Add-Text $s $kicker 58 25 840 20 11 $C.TealDark 'Microsoft YaHei' -1 1 | Out-Null }
  Add-Text $s $title 58 48 850 68 32 $C.Ink 'Microsoft YaHei' -1 1 | Out-Null
  $bar=$s.Shapes.AddShape(1,58,120,42,4); $bar.Fill.ForeColor.RGB=$C.TealDark; $bar.Line.Visible=0
}
function Add-Footer($s,[int]$n,[string]$tag='视觉编辑层定位') {
  Add-Text $s $tag 58 510 260 14 9 $C.Gray 'Microsoft YaHei' 0 1 | Out-Null
  Add-Text $s ([string]$n) 884 508 20 14 9 $C.Gray 'Arial' 0 2 | Out-Null
}
function Add-Note($s,[string]$note) {
  try {
    $ph=$s.NotesPage.Shapes.Placeholders(2)
    $ph.TextFrame.TextRange.Text=$note
  } catch {}
}
function New-Slide([int]$n,[int]$bg=$C.White) {
  $s=$pres.Slides.Add($pres.Slides.Count+1,12)
  $s.FollowMasterBackground=0; $s.Background.Fill.ForeColor.RGB=$bg
  Add-Footer $s $n
  return $s
}
function Add-FlowArrow($s,[double]$x,[double]$y,[double]$w=34) { Add-Line $s $x $y ($x+$w) $y $C.Gray 1.8 -arrow | Out-Null }
function Add-MetricCard($s,[string]$value,[string]$label,[double]$x,[double]$y,[double]$w,[int]$accent=$C.Blue) {
  $card=Add-Box $s '' $x $y $w 98 $C.White $C.Line 12 $C.Ink 0 0 1
  $accentBar=$s.Shapes.AddShape(1,$x,$y,6,98); $accentBar.Fill.ForeColor.RGB=$accent; $accentBar.Line.Visible=0
  Add-Text $s $value ($x+18) ($y+13) ($w-28) 38 26 $accent 'Arial' -1 1 | Out-Null
  Add-Text $s $label ($x+18) ($y+56) ($w-28) 30 12 $C.Muted 'Microsoft YaHei' 0 1 | Out-Null
}

# 1 Cover
$s=New-Slide 1 $C.Light
$s.Shapes.AddPicture($hero,0,-1,560,56,365,410) | Out-Null
Add-Text $s '视觉编辑层定位' 58 92 470 58 36 $C.Ink 'Microsoft YaHei' -1 1 | Out-Null
Add-Text $s '从 7 种定位策略到知识增强视觉语言模型编辑' 58 155 500 62 24 $C.TealDark 'Microsoft YaHei' -1 1 | Out-Null
Add-Text $s '方法原理 · 候选层验证 · 综合对比 · 后续工作' 58 235 480 28 16 $C.Muted 'Microsoft YaHei' 0 1 | Out-Null
Add-Box $s '核心观点  定位只是第一步：先找对层，再构建知识子图并完成双路径编辑与可解释分析。' 58 315 472 82 $C.White $C.Line 15 $C.Ink 0 0 1 | Out-Null
Add-Text $s '研究汇报 / 可编辑版' 58 451 280 18 11 $C.Gray 'Microsoft YaHei' 0 1 | Out-Null
Add-Note $s '[Sources] 用户提供的视觉编辑层定位1.pptx；mywork-通用版.docx。' 

# 2 Executive scorecard
$s=New-Slide 2
Add-Title $s '先看结论：Ours 在现有证据上呈现最稳定的整体优势' 'EXECUTIVE SUMMARY'
Add-MetricCard $s '#1 / 11' '按平均 Spearman 排名' 58 142 170 $C.Violet
Add-MetricCard $s '15 / 18' '模型×数据集组合为正相关' 242 142 170 $C.TealDark
Add-MetricCard $s '6 / 6' '相对基线的平均 Best 与 Mean 均为正' 426 142 210 $C.Blue
Add-MetricCard $s '72.2%' '54 次配对中的不败比例' 650 142 210 $C.Orange
Add-Box $s '平均提升（Top-3 候选真实编辑）' 58 276 802 36 $C.Dark $C.Dark 15 $C.White 0 -1 2 | Out-Null
Add-Box $s '+3.07  Best@3' 58 322 250 74 $C.BlueLight $C.Blue 22 $C.Blue 0 -1 2 | Out-Null
Add-Box $s '+1.97  Mean@3' 320 322 250 74 $C.GreenLight $C.Green 22 $C.Green 0 -1 2 | Out-Null
Add-Box $s '30 胜 / 9 平 / 15 负' 582 322 278 74 $C.OrangeLight $C.Orange 20 $C.Orange 0 -1 2 | Out-Null
Add-Text $s '说明：这是描述性优势；当前严格配对样本量有限，Wilcoxon 尚未达到 p<0.05。' 58 429 802 30 13 $C.Muted 'Microsoft YaHei' 0 1 | Out-Null
Add-Note $s '[Sources] visual formula analysis outputs, 2026-07-31；六个基线的 Ours-minus-baseline 配对汇总。'

# 3 Full pipeline
$s=New-Slide 3 $C.Light
Add-Title $s '完整任务链：定位决定“改哪里”，但不等于编辑完成' 'END-TO-END TASK'
$steps=@(
  @('1','候选层定位','7种方法输出 Top-K',$C.Violet),@('2','真实扫层验证','统一训练/独立评测',$C.Blue),@('3','知识子图构建','实体—关系—证据',$C.TealDark),
  @('4','双路径知识注入','参数记忆 + 外部检索',$C.Green),@('5','多维编辑评测','可靠性/泛化/局部性',$C.Orange),@('6','交互可视分析','解释定位与编辑差异',$C.Red)
)
$x=45
for($i=0;$i -lt $steps.Count;$i++){
  $a=$steps[$i]; Add-Circle $s $a[0] $x 175 42 $a[3] | Out-Null
  Add-Box $s ($a[1]+"`n"+$a[2]) ($x-18) 230 118 100 $C.White $a[3] 14 $C.Ink 0 $(if($i -eq 0){-1}else{0}) 2 | Out-Null
  if($i -lt 5){Add-FlowArrow $s ($x+102) 280 31}
  $x+=148
}
Add-Box $s '本次重点' 38 353 140 38 $C.Violet $C.Violet 14 $C.White 0 -1 2 | Out-Null
Add-Text $s '先证明候选层预测能缩小搜索空间并保留高编辑性能，再把定位结果接入后续知识增强编辑系统。' 194 355 662 54 15 $C.Ink 'Microsoft YaHei' 0 1 | Out-Null
Add-Note $s '[Sources] mywork-通用版.docx；任务安排文档。'

# 4 Protocol
$s=New-Slide 4
Add-Title $s '公平比较协议：不同分数统一落到同一真实编辑实验' 'VALIDATION PROTOCOL'
$xs=@(58,238,418,598,778); $labels=@('定位分数','Top-3 / Top-5','同构编辑器','独立 test/eval','多指标比较')
$subs=@('每种方法各自计算','不比较原始分数尺度','相同层容量与训练配置','禁止用训练集评测','Best / Mean / Regret')
$colors=@($C.Violet,$C.Blue,$C.TealDark,$C.Green,$C.Orange)
for($i=0;$i -lt 5;$i++){
  Add-Circle $s ([string]($i+1)) ($xs[$i]+50) 155 40 $colors[$i] | Out-Null
  Add-Box $s ($labels[$i]+"`n"+$subs[$i]) $xs[$i] 215 135 115 $C.White $colors[$i] 14 $C.Ink 0 -1 2 | Out-Null
  if($i -lt 4){Add-FlowArrow $s ($xs[$i]+136) 272 36}
}
Add-Box $s '完成判定：selected_checkpoint.tsv + eval_full.done + 完整正式评测结果，缺一不可。' 58 380 855 54 $C.GreenLight $C.Green 15 $C.Ink 0 -1 2 | Out-Null
Add-Note $s '[Sources] 实验统一验收规范；6location_7model_3datas_top_3_5_layers_outcome.md。'

# 5 Divider
$s=New-Slide 5 $C.Teal
$s.Shapes(1).Delete(); $s.Shapes(1).Delete()
Add-Text $s '第一部分' 70 105 240 34 18 $C.TealDark 'Microsoft YaHei' -1 1 | Out-Null
Add-Text $s '7 种视觉编辑层定位方法' 70 155 720 62 36 $C.Ink 'Microsoft YaHei' -1 1 | Out-Null
Add-Text $s '从启发式先验、贡献归因、梯度显著性、扰动因果，到视觉梯度方向与幅值的联合建模' 70 246 760 60 18 $C.Muted 'Microsoft YaHei' 0 1 | Out-Null
Add-Box $s '统一输出：Top-K 候选层 → 真实训练 → 独立评测' 70 350 560 56 $C.White $C.White 16 $C.Ink 0 -1 2 | Out-Null

# 6 Overview taxonomy
$s=New-Slide 6
Add-Title $s '七种方法不是“同一种分数”：它们回答不同的定位问题' 'METHOD TAXONOMY'
$methods=@(
  @('Middle','深度先验','中层是否更可编辑？',$C.Gray),@('VisEdit','模块贡献','哪些层贡献视觉答案？',$C.Blue),@('SaLEM','参数梯度','哪层参数最敏感？',$C.TealDark),
  @('LGA','新旧梯度','哪层最支持知识替换？',$C.Violet),@('Perturb-KL','视觉扰动','哪层最影响输出分布？',$C.Orange),@('CMA','因果干预','恢复哪层能挽回答案？',$C.Red),@('Ours','视觉梯度','哪层同时强且方向一致？',$C.Green)
)
for($i=0;$i -lt 7;$i++){
  $row=[math]::Floor($i/4); $col=$i%4; $x=58+$col*218; $y=135+$row*150
  if($i -eq 6){$x=494}
  Add-Box $s $methods[$i][0] $x $y 190 38 $methods[$i][3] $methods[$i][3] 16 $C.White 0 -1 2 | Out-Null
  Add-Box $s ($methods[$i][1]+"`n"+$methods[$i][2]) $x ($y+42) 190 78 $C.White $methods[$i][3] 13 $C.Ink 0 0 2 | Out-Null
}
Add-Text $s 'Perturb-KL-Pre 仅作为消融，不计入 7 个正式基线/方法。' 58 455 540 20 12 $C.Muted 'Microsoft YaHei' 0 1 | Out-Null
Add-Note $s '[Sources] 6edit_layer_localization_candidate_methods_简洁说明版.md。'

# 7 Middle
$s=New-Slide 7 $C.Light
Add-Title $s '1  Middle-Prior-Direct：以网络深度中部作为无需样本的先验' 'METHOD 01 · HEURISTIC PRIOR'
Add-Box $s '输入' 58 140 100 42 $C.Dark $C.Dark 14 $C.White 0 -1 2 | Out-Null
Add-Box $s '模型总层数 L' 58 190 150 62 $C.White $C.Line 15 $C.Ink 0 -1 2 | Out-Null
Add-FlowArrow $s 214 221 42
Add-Box $s '计算中点 m=(L−1)/2' 262 190 188 62 $C.BlueLight $C.Blue 15 $C.Blue 0 -1 2 | Out-Null
Add-FlowArrow $s 456 221 42
Add-Box $s '按 |l−m| 升序' 504 190 150 62 $C.White $C.Blue 15 $C.Ink 0 -1 2 | Out-Null
Add-FlowArrow $s 660 221 42
Add-Box $s '输出 Top-K 中层' 708 190 170 62 $C.GreenLight $C.Green 15 $C.Green 0 -1 2 | Out-Null
$start=98; for($i=0;$i -lt 16;$i++){ $fill=if($i -in 7,8,9){$C.Blue}else{$C.White}; $co=if($i -in 7,8,9){$C.White}else{$C.Muted}; Add-Box $s ([string]$i) ($start+$i*47) 313 38 46 $fill $C.Line 12 $co 0 $(if($i -in 7,8,9){-1}else{0}) 2 | Out-Null }
Add-Text $s '优点：零样本、成本最低、作为必要启发式基线。' 58 395 390 24 14 $C.Ink 'Microsoft YaHei' 0 1 | Out-Null
Add-Text $s '局限：不读取样本与视觉信号，不能解释模型/数据集差异。' 470 395 410 42 14 $C.Red 'Microsoft YaHei' 0 1 | Out-Null
Add-Note $s '[Sources] 方法手册：Middle-Prior-Direct。'

# 8 VisEdit
$s=New-Slide 8
Add-Title $s '2  VisEdit-Contrib-Pre-KeyToken：用关键 token 的前向模块贡献定位' 'METHOD 02 · FORWARD ATTRIBUTION'
Add-Box $s '图像 + 问题' 58 154 140 58 $C.BlueLight $C.Blue 15 $C.Ink 0 -1 2 | Out-Null
Add-FlowArrow $s 204 183 35
Add-Box $s '冻结 VLM 前向' 245 154 140 58 $C.White $C.Blue 15 $C.Ink 0 -1 2 | Out-Null
Add-FlowArrow $s 391 183 35
Add-Box $s '提取关键答案 token' 432 154 170 58 $C.VioletLight $C.Violet 15 $C.Ink 0 -1 2 | Out-Null
Add-FlowArrow $s 608 183 35
Add-Box $s '逐层模块贡献' 649 154 140 58 $C.White $C.Violet 15 $C.Ink 0 -1 2 | Out-Null
Add-FlowArrow $s 795 183 26
Add-Box $s 'Top-K' 827 154 80 58 $C.GreenLight $C.Green 15 $C.Green 0 -1 2 | Out-Null
Add-Text $s '层贡献曲线（示意）' 58 270 220 24 14 $C.Muted 'Microsoft YaHei' -1 1 | Out-Null
$vals=@(16,20,24,32,38,45,57,63,71,78,85,72,61,49,35,26)
for($i=0;$i -lt $vals.Count;$i++){ $h=$vals[$i]; $x=85+$i*46; $fill=if($i -in 8,9,10){$C.Blue}else{$C.Line}; $r=$s.Shapes.AddShape(1,$x,(396-$h),28,$h); $r.Fill.ForeColor.RGB=$fill; $r.Line.Visible=0; Add-Text $s ([string]$i) ($x-2) 402 32 16 9 $C.Gray 'Arial' 0 2 | Out-Null }
Add-Box $s '结果解释：高贡献层更可能决定视觉答案，但“贡献高”仍需真实编辑验证。' 58 441 820 38 $C.Light $C.Line 13 $C.Ink 0 0 2 | Out-Null
Add-Note $s '[Sources] 方法手册：VisEdit-Contrib-Pre-KeyToken。'

# 9 SaLEM
$s=New-Slide 9 $C.Light
Add-Title $s '3  SaLEM-Alt-Direct：从参数梯度显著性逐级汇聚到层' 'METHOD 03 · PARAMETER SALIENCY'
$x0=65
Add-Box $s '目标答案损失' $x0 150 145 64 $C.VioletLight $C.Violet 15 $C.Ink 0 -1 2 | Out-Null
Add-FlowArrow $s 216 182 35
Add-Box $s '反向传播 ∇θL' 257 150 145 64 $C.White $C.Violet 15 $C.Ink 0 -1 2 | Out-Null
Add-FlowArrow $s 408 182 35
Add-Box $s '参数显著性' 449 150 125 64 $C.BlueLight $C.Blue 15 $C.Ink 0 -1 2 | Out-Null
Add-FlowArrow $s 580 182 35
Add-Box $s '列/矩阵汇聚' 621 150 125 64 $C.White $C.Blue 15 $C.Ink 0 -1 2 | Out-Null
Add-FlowArrow $s 752 182 35
Add-Box $s '层分数 Top-K' 793 150 120 64 $C.GreenLight $C.Green 15 $C.Green 0 -1 2 | Out-Null
Add-Text $s '显著性漏斗' 58 270 160 25 14 $C.Muted 'Microsoft YaHei' -1 1 | Out-Null
$ys=@(305,350,392); $ws=@(760,540,320); $labs=@('参数级：每个可编辑矩阵的梯度响应','结构级：列/矩阵聚合并归一化','层级：同层模块汇总，排序输出')
for($i=0;$i -lt 3;$i++){ $x=480-$ws[$i]/2; $poly=$s.Shapes.AddShape(7,$x,$ys[$i],$ws[$i],34); $poly.Fill.ForeColor.RGB=@($C.VioletLight,$C.BlueLight,$C.GreenLight)[$i]; $poly.Line.ForeColor.RGB=@($C.Violet,$C.Blue,$C.Green)[$i]; Add-Text $s $labs[$i] ($x+20) ($ys[$i]+7) ($ws[$i]-40) 20 12 $C.Ink 'Microsoft YaHei' $(if($i -eq 2){-1}else{0}) 2 | Out-Null }
Add-Text $s '优势：直接反映参数可塑性。局限：可能偏向梯度尺度较大的模块，视觉特异性有限。' 58 454 850 23 13 $C.Muted 'Microsoft YaHei' 0 1 | Out-Null
Add-Note $s '[Sources] 方法手册：SaLEM-Alt-Direct。'

# 10 LGA
$s=New-Slide 10
Add-Title $s '4  LGA-Param-Direct-AltModelPred：用新旧知识梯度关系衡量替换方向' 'METHOD 04 · GRADIENT ALIGNMENT'
Add-Box $s '旧知识目标 y_old' 75 150 170 58 $C.RedLight $C.Red 15 $C.Ink 0 -1 2 | Out-Null
Add-Box $s '新知识目标 y_new' 75 240 170 58 $C.GreenLight $C.Green 15 $C.Ink 0 -1 2 | Out-Null
Add-FlowArrow $s 252 179 45; Add-FlowArrow $s 252 269 45
Add-Box $s 'g_old = ∇θL_old' 303 150 190 58 $C.White $C.Red 16 $C.Red 0 -1 2 | Out-Null
Add-Box $s 'g_new = ∇θL_new' 303 240 190 58 $C.White $C.Green 16 $C.Green 0 -1 2 | Out-Null
Add-Line $s 500 179 580 223 $C.Red 1.8 -arrow | Out-Null; Add-Line $s 500 269 580 223 $C.Green 1.8 -arrow | Out-Null
Add-Box $s "逐层计算`n方向一致 / 冲突`n与梯度幅值" 586 174 170 98 $C.VioletLight $C.Violet 15 $C.Ink 0 -1 2 | Out-Null
Add-FlowArrow $s 762 223 40
Add-Box $s 'Top-K 编辑层' 808 194 110 58 $C.GreenLight $C.Green 15 $C.Green 0 -1 2 | Out-Null
Add-Box $s '定位原理' 75 348 120 40 $C.Dark $C.Dark 14 $C.White 0 -1 2 | Out-Null
Add-Text $s '优先选择“支持新知识写入、同时能抑制旧知识”的层，而不只是梯度大的层。' 214 350 650 42 16 $C.Ink 'Microsoft YaHei' 0 1 | Out-Null
Add-Text $s '结果含义：候选层体现知识替换方向；对视觉路径的特异性仍依赖目标与样本设计。' 75 425 800 24 13 $C.Muted 'Microsoft YaHei' 0 1 | Out-Null
Add-Note $s '[Sources] 方法手册：LGA-Param-Direct-AltModelPred。'

# 11 Perturb image
$s=New-Slide 11
$img=Join-Path $refDir '幻灯片12.PNG'
$s.Shapes.AddPicture($img,0,-1,55,94,660,372) | Out-Null
Add-Box $s '5  Perturb-KL-Direct-AltSeq' 58 35 470 48 $C.Orange $C.Orange 24 $C.White 0 -1 1 | Out-Null
Add-Box $s '核心：只扰动视觉 token，比较干净/扰动输出分布的 KL 差异。' 735 118 180 100 $C.OrangeLight $C.Orange 14 $C.Ink 0 -1 2 | Out-Null
Add-Box $s "强项`n具有视觉特异性`n接近因果敏感度" 735 238 180 90 $C.White $C.Green 14 $C.Green 0 -1 2 | Out-Null
Add-Box $s "边界`n敏感层 ≠ 最佳编辑层`n必须真实扫层验证" 735 348 180 92 $C.White $C.Red 14 $C.Red 0 -1 2 | Out-Null
Add-Note $s '[Sources] 用户参考PPT第12页；方法手册：Perturb-KL-Direct-AltSeq。'

# 12 CMA image
$s=New-Slide 12
$img=Join-Path $refDir '幻灯片33.PNG'
$s.Shapes.AddPicture($img,0,-1,55,94,660,372) | Out-Null
$cover=$s.Shapes.AddShape(1,55,112,150,92); $cover.Fill.ForeColor.RGB=$C.White; $cover.Line.Visible=0
Add-Box $s '6  CMA-Direct' 58 35 330 48 $C.Red $C.Red 24 $C.White 0 -1 1 | Out-Null
Add-Box $s '核心：对中间状态做因果恢复，观察目标答案概率能恢复多少。' 735 118 180 100 $C.RedLight $C.Red 14 $C.Ink 0 -1 2 | Out-Null
Add-Box $s "强项`n干预式解释`n因果语义最明确" 735 238 180 90 $C.White $C.Green 14 $C.Green 0 -1 2 | Out-Null
Add-Box $s "现状`n有效覆盖 31/214`n覆盖率 14.5%" 735 348 180 92 $C.White $C.Orange 14 $C.Orange 0 -1 2 | Out-Null
Add-Note $s '[Sources] 用户参考PPT第33页；CMA实验状态与覆盖统计。'

# 13 Ours image
$s=New-Slide 13
$img=Join-Path $refDir '幻灯片28.PNG'
$s.Shapes.AddPicture($img,0,-1,55,94,660,372) | Out-Null
Add-Box $s '7  Ours — VisualGradient-Direct' 58 35 500 48 $C.Green $C.Green 23 $C.White 0 -1 1 | Out-Null
Add-Box $s '主公式' 735 112 180 34 $C.Dark $C.Dark 14 $C.White 0 -1 2 | Out-Null
Add-Box $s '|Sᵥ_cos| × Sᵥ_new_norm' 735 153 180 64 $C.GreenLight $C.Green 17 $C.Green 0 -1 2 | Out-Null
Add-Box $s "#1 / 11`n平均 Spearman 0.323" 735 238 180 78 $C.White $C.Violet 16 $C.Violet 0 -1 2 | Out-Null
Add-Box $s "15 / 18 正相关`n跨模型/数据更稳定" 735 338 180 82 $C.White $C.Blue 15 $C.Blue 0 -1 2 | Out-Null
Add-Note $s '[Sources] 用户参考PPT第28页；11公式汇总分析。'

# 14 Ours formulas
$s=New-Slide 14 $C.Light
Add-Title $s 'Ours 的关键：把“方向一致性”和“新知识写入强度”分开测，再组合' 'OURS · FORMULA DESIGN'
Add-Box $s '视觉目标梯度 gᵥ' 58 150 165 58 $C.BlueLight $C.Blue 15 $C.Ink 0 -1 2 | Out-Null
Add-Box $s '新知识梯度 g_new' 58 240 165 58 $C.GreenLight $C.Green 15 $C.Ink 0 -1 2 | Out-Null
Add-Line $s 230 179 330 225 $C.Blue 1.8 -arrow | Out-Null; Add-Line $s 230 269 330 225 $C.Green 1.8 -arrow | Out-Null
Add-Box $s "方向项`nSᵥ_cos = cos(gᵥ,g_new)" 338 140 240 72 $C.VioletLight $C.Violet 15 $C.Ink 0 -1 2 | Out-Null
Add-Box $s "幅值项`nSᵥ_new_norm = ||g_new||" 338 238 240 72 $C.GreenLight $C.Green 15 $C.Ink 0 -1 2 | Out-Null
Add-Line $s 585 176 678 222 $C.Violet 1.8 -arrow | Out-Null; Add-Line $s 585 274 678 222 $C.Green 1.8 -arrow | Out-Null
Add-Box $s "联合评分`n|Sᵥ_cos| × Sᵥ_new_norm" 686 174 220 98 $C.Dark $C.Dark 18 $C.White 0 -1 2 | Out-Null
Add-Box $s '7 个基础视觉梯度公式' 58 358 250 48 $C.White $C.Blue 15 $C.Blue 0 -1 2 | Out-Null
Add-Box $s '+' 322 358 46 48 $C.White $C.Line 18 $C.Muted 0 -1 2 | Out-Null
Add-Box $s '4 个深度加权 Ours 指标' 382 358 270 48 $C.White $C.Violet 15 $C.Violet 0 -1 2 | Out-Null
Add-Box $s '共 11 个公式统一排序与真实编辑验证' 666 358 240 48 $C.GreenLight $C.Green 14 $C.Green 0 -1 2 | Out-Null
Add-Text $s '当前最优并不是“只靠深层先验”，而是无深度项的 M_abscos_x_newn。' 58 440 830 24 14 $C.Ink 'Microsoft YaHei' -1 1 | Out-Null
Add-Note $s '[Sources] visual_candidate_formula_rankings.csv；11公式分析输出。'

# 15 Layer heatmap
$s=New-Slide 15
Add-Title $s '候选层热力图：不同方法覆盖不同深度，Ours 聚焦浅层视觉写入区' 'EXAMPLE · MMKE-VISUAL × QWEN2.5-VL'
$rows=@(
  @('Middle',17,18,16,$C.Gray),@('VisEdit',28,27,26,$C.Blue),@('SaLEM',12,11,14,$C.TealDark),@('LGA',2,30,1,$C.Violet),@('Perturb',0,13,14,$C.Orange),@('CMA',1,0,6,$C.Red),@('Ours',0,1,2,$C.Green)
)
$x0=154; $cell=22; $y0=145
for($i=0;$i -le 30;$i++){ if($i%2 -eq 0){Add-Text $s ([string]$i) ($x0+$i*$cell-2) 120 24 16 8 $C.Gray 'Arial' 0 2 | Out-Null} }
for($r=0;$r -lt $rows.Count;$r++){
  $y=$y0+$r*43; Add-Text $s $rows[$r][0] 58 ($y+6) 85 18 12 $C.Ink 'Arial' $(if($r -eq 6){-1}else{0}) 1 | Out-Null
  for($i=0;$i -le 30;$i++){ $hit=$i -in @($rows[$r][1],$rows[$r][2],$rows[$r][3]); $fill=if($hit){$rows[$r][4]}else{$C.Light}; $sh=$s.Shapes.AddShape(1,$x0+$i*$cell,$y,19,28); $sh.Fill.ForeColor.RGB=$fill; $sh.Line.ForeColor.RGB=$C.White }
}
Add-Box $s '解读' 58 463 80 32 $C.Dark $C.Dark 12 $C.White 0 -1 2 | Out-Null
Add-Text $s '该例用于展示候选多样性，不作为 Ours 优势的唯一证据；最终以跨组合真实编辑汇总判断。' 150 465 755 26 12 $C.Muted 'Microsoft YaHei' 0 1 | Out-Null
Add-Note $s '[Sources] MMKE-visual × Qwen2.5-VL 各方法 Top-3；本地结果总表。'

# 16 Method property matrix
$s=New-Slide 16 $C.Light
Add-Title $s '方法对比矩阵：Ours 兼具视觉特异性与方向建模' 'COMPREHENSIVE METHOD COMPARISON'
$cols=@('方法','信号','视觉特异','新旧关系','干预/因果','相对成本','主要局限')
$data=@(
  @('Middle','深度','—','—','—','极低','忽略样本'),@('VisEdit','贡献','●','—','—','低','贡献≠可编辑'),@('SaLEM','梯度','△','—','—','中','尺度偏置'),
  @('LGA','双梯度','△','●','—','中','视觉性有限'),@('Perturb','KL扰动','●','—','△','高','敏感≠最佳'),@('CMA','状态恢复','●','△','●','很高','覆盖率低'),@('Ours','视觉双梯度','●','●','△','中','需扩大实证')
)
$widths=@(112,112,104,104,104,104,170); $x=48
for($ci=0;$ci -lt $cols.Count;$ci++){ Add-Box $s $cols[$ci] $x 132 $widths[$ci] 40 $C.Dark $C.White 12 $C.White 0 -1 2 | Out-Null; $x+=$widths[$ci] }
for($r=0;$r -lt $data.Count;$r++){
  $x=48; $y=172+$r*41; $bg=if($r -eq 6){$C.GreenLight}else{if($r%2 -eq 0){$C.White}else{$C.Light}}
  for($ci=0;$ci -lt $cols.Count;$ci++){ $co=if($r -eq 6 -and $ci -eq 0){$C.Green}else{$C.Ink}; Add-Box $s $data[$r][$ci] $x $y $widths[$ci] 41 $bg $C.Line 11 $co 0 $(if($r -eq 6){-1}else{0}) 2 | Out-Null; $x+=$widths[$ci] }
}
Add-Text $s '● 强   △ 部分具备   — 不具备 / 不直接建模' 48 470 400 18 10 $C.Muted 'Microsoft YaHei' 0 1 | Out-Null
Add-Note $s '[Sources] 七种方法定义与计算流程；方法手册。'

# 17 empirical heatmap
$s=New-Slide 17
Add-Title $s '跨基线真实编辑：Ours 对六种基线平均差均为正' 'EMPIRICAL COMPARISON · K=3'
$base=@('Middle','VisEdit','SaLEM','LGA','Perturb-KL','CMA')
$best=@(2.662,4.133,2.792,1.284,4.021,3.538)
$mean=@(0.601,1.795,1.341,2.345,2.771,2.960)
$wtl=@('6/0/3','5/0/4','6/0/3','6/1/2','3/5/1','4/3/2')
$x0=215; $cw=104
Add-Box $s '指标' 58 140 150 42 $C.Dark $C.Dark 13 $C.White 0 -1 2 | Out-Null
for($i=0;$i -lt 6;$i++){Add-Box $s $base[$i] ($x0+$i*$cw) 140 $cw 42 $C.Dark $C.White 12 $C.White 0 -1 2 | Out-Null}
$rowLabs=@('Δ Best@3','Δ Mean@3','胜/平/负')
for($r=0;$r -lt 3;$r++){
  $y=182+$r*72; Add-Box $s $rowLabs[$r] 58 $y 150 72 $C.Light $C.Line 14 $C.Ink 0 -1 2 | Out-Null
  for($i=0;$i -lt 6;$i++){
    if($r -eq 0){$v=$best[$i];$txt=('+'+$v.ToString('0.00'));$fill=if($v -ge 3){$C.Green}else{$C.GreenLight};$co=if($v -ge 3){$C.White}else{$C.Green}}
    elseif($r -eq 1){$v=$mean[$i];$txt=('+'+$v.ToString('0.00'));$fill=if($v -ge 2){$C.Blue}else{$C.BlueLight};$co=if($v -ge 2){$C.White}else{$C.Blue}}
    else{$txt=$wtl[$i];$fill=$C.White;$co=$C.Ink}
    Add-Box $s $txt ($x0+$i*$cw) $y $cw 72 $fill $C.Line 16 $co 0 -1 2 | Out-Null
  }
}
Add-Box $s '平均' 58 418 150 42 $C.Dark $C.Dark 13 $C.White 0 -1 2 | Out-Null
Add-Box $s 'Best@3  +3.07' 215 418 300 42 $C.GreenLight $C.Green 16 $C.Green 0 -1 2 | Out-Null
Add-Box $s 'Mean@3  +1.97' 530 418 309 42 $C.BlueLight $C.Blue 16 $C.Blue 0 -1 2 | Out-Null
Add-Note $s '[Sources] Ours-minus-baseline pairwise summary；K=3严格配对。'

# 18 scorecard detailed
$s=New-Slide 18 $C.Light
Add-Title $s '为什么说 Ours 更好：多维证据方向一致' 'EVIDENCE SCORECARD'
$cards=@(
  @('公式质量','平均 Spearman 0.323','11个公式中第1',$C.Violet),@('跨组合稳定性','15/18 为正相关','覆盖多模型×数据',$C.TealDark),
  @('真实编辑收益','6/6 基线平均差为正','Best 与 Mean 同时提升',$C.Blue),@('失败风险','72.2% 不败','30胜 / 9平 / 15负',$C.Orange)
)
for($i=0;$i -lt 4;$i++){
  $x=58+($i%2)*418; $y=145+[math]::Floor($i/2)*142
  Add-Box $s $cards[$i][0] $x $y 390 35 $cards[$i][3] $cards[$i][3] 14 $C.White 0 -1 2 | Out-Null
  Add-Box $s ($cards[$i][1]+"`n"+$cards[$i][2]) $x ($y+39) 390 86 $C.White $cards[$i][3] 18 $C.Ink 0 -1 2 | Out-Null
}
Add-Box $s '结论措辞' 58 438 120 36 $C.Dark $C.Dark 13 $C.White 0 -1 2 | Out-Null
Add-Text $s '现有结果支持“Ours 更有希望、更稳定地命中高性能候选层”，而不是宣称已完成统计显著性证明。' 194 439 700 36 14 $C.Ink 'Microsoft YaHei' -1 1 | Out-Null
Add-Note $s '[Sources] 11公式分析；六基线真实编辑配对汇总。'

# 19 boundaries
$s=New-Slide 19
Add-Title $s '证据边界：把优势讲清楚，也把尚未完成的证明讲清楚' 'EVIDENCE BOUNDARIES'
$left=@('✓ 11 个公式已统一比较','✓ Ours 主公式平均相关性最高','✓ 六个基线平均 Best/Mean 差均为正','✓ 真实编辑使用独立 test/eval')
$right=@('△ Top-3 完整结果仅覆盖 9/19 组合','△ 严格配对 Wilcoxon 均未达 p<0.05','△ measured-layer oracle 不是全层 oracle','△ PaliGemma main / stable 必须分开报告')
Add-Box $s '已经支持的结论' 58 140 380 42 $C.Green $C.Green 16 $C.White 0 -1 2 | Out-Null
Add-Box $s '仍需补强的证据' 522 140 380 42 $C.Orange $C.Orange 16 $C.White 0 -1 2 | Out-Null
for($i=0;$i -lt 4;$i++){ Add-Box $s $left[$i] 58 (192+$i*58) 380 46 $C.GreenLight $C.Green 13 $C.Ink 0 0 1 | Out-Null; Add-Box $s $right[$i] 522 (192+$i*58) 380 46 $C.OrangeLight $C.Orange 13 $C.Ink 0 0 1 | Out-Null }
Add-Note $s '[Sources] 结果完整性审计；PaliGemma配置说明；统计检验输出。'

# 20 divider
$s=New-Slide 20 $C.Teal
$s.Shapes(1).Delete(); $s.Shapes(1).Delete()
Add-Text $s '第二部分' 70 105 240 34 18 $C.TealDark 'Microsoft YaHei' -1 1 | Out-Null
Add-Text $s '定位之后：知识增强视觉语言模型编辑' 70 155 800 62 34 $C.Ink 'Microsoft YaHei' -1 1 | Out-Null
Add-Text $s '把候选层转化为可控、可解释、可复现的知识编辑系统' 70 246 760 60 18 $C.Muted 'Microsoft YaHei' 0 1 | Out-Null
Add-Box $s '知识子图 → 双路径注入 → 多维评测 → 交互分析' 70 350 620 56 $C.White $C.White 16 $C.Ink 0 -1 2 | Out-Null

# 21 KG subgraph
$s=New-Slide 21 $C.Light
Add-Title $s '下一步 1：从编辑样本构建可追溯的知识子图' 'KNOWLEDGE SUBGRAPH'
Add-Box $s "编辑样本`n图像 + 问题 + 新事实" 58 190 170 92 $C.BlueLight $C.Blue 15 $C.Ink 0 -1 2 | Out-Null
Add-FlowArrow $s 235 236 48
Add-Box $s "实体对齐`n视觉实体 ↔ 文本实体" 289 190 170 92 $C.VioletLight $C.Violet 15 $C.Ink 0 -1 2 | Out-Null
Add-FlowArrow $s 466 236 48
Add-Box $s "关系扩展`n1-hop / 2-hop 证据" 520 190 170 92 $C.GreenLight $C.Green 15 $C.Ink 0 -1 2 | Out-Null
Add-FlowArrow $s 697 236 48
Add-Box $s "可追溯子图`n实体—关系—来源" 751 190 170 92 $C.OrangeLight $C.Orange 15 $C.Ink 0 -1 2 | Out-Null
$nodes=@(@('主实体',440,345,$C.Blue),@('新事实',560,325,$C.Green),@('证据A',650,390,$C.Orange),@('关系',515,420,$C.Violet),@('证据B',355,410,$C.TealDark))
for($i=0;$i -lt $nodes.Count;$i++){if($i -gt 0){Add-Line $s 490 375 ($nodes[$i][1]+32) ($nodes[$i][2]+18) $C.Gray 1.2 | Out-Null}; Add-Circle $s $nodes[$i][0] $nodes[$i][1] $nodes[$i][2] 64 $nodes[$i][3] $C.White 11 | Out-Null}
Add-Note $s '[Sources] mywork-通用版.docx；后续知识增强任务设计。'

# 22 Dual route
$s=New-Slide 22
Add-Title $s '下一步 2：候选层上的参数记忆与外部知识双路径注入' 'DUAL-ROUTE EDITING'
Add-Box $s '候选编辑层 l*' 58 222 170 68 $C.Dark $C.Dark 17 $C.White 0 -1 2 | Out-Null
Add-Line $s 235 256 340 182 $C.Violet 2 -arrow | Out-Null
Add-Line $s 235 256 340 332 $C.Blue 2 -arrow | Out-Null
Add-Box $s "路径 A：参数内编辑`n轻量适配器写入新事实" 348 130 250 102 $C.VioletLight $C.Violet 16 $C.Ink 0 -1 2 | Out-Null
Add-Box $s "路径 B：知识检索增强`n子图证据动态注入" 348 286 250 102 $C.BlueLight $C.Blue 16 $C.Ink 0 -1 2 | Out-Null
Add-Line $s 605 181 700 256 $C.Violet 2 -arrow | Out-Null
Add-Line $s 605 337 700 256 $C.Blue 2 -arrow | Out-Null
Add-Box $s "门控融合`n按问题与视觉证据分配权重" 708 203 205 106 $C.GreenLight $C.Green 16 $C.Ink 0 -1 2 | Out-Null
Add-Box $s '目标：可靠写入 + 泛化保持 + 局部性约束 + 可追溯证据' 148 429 670 48 $C.Light $C.Line 15 $C.Ink 0 -1 2 | Out-Null
Add-Note $s '[Sources] mywork-通用版.docx；双路径知识注入设计。'

# 23 interactive analytics
$s=New-Slide 23 $C.Light
Add-Title $s '下一步 3：把“为什么选这一层”做成交互式可视分析' 'INTERACTIVE VISUAL ANALYTICS'
Add-Box $s "筛选器`n模型 / 数据集 / 方法 / 配置" 58 145 195 105 $C.White $C.Blue 15 $C.Ink 0 -1 2 | Out-Null
Add-Box $s "层热力图`n分数 × 真实编辑效果" 270 145 195 105 $C.White $C.Violet 15 $C.Ink 0 -1 2 | Out-Null
Add-Box $s "方法对比`nTop-K重合 / Regret / WTL" 482 145 195 105 $C.White $C.TealDark 15 $C.Ink 0 -1 2 | Out-Null
Add-Box $s "证据追踪`ncheckpoint / eval / 异常状态" 694 145 195 105 $C.White $C.Orange 15 $C.Ink 0 -1 2 | Out-Null
for($i=0;$i -lt 3;$i++){Add-FlowArrow $s (254+$i*212) 198 14}
Add-Text $s '示意：预测分数与真实编辑效果的联合层图' 58 296 390 24 14 $C.Muted 'Microsoft YaHei' -1 1 | Out-Null
$vals1=@(12,18,28,42,58,72,84,65,48,34,22,17,11,9); $vals2=@(18,23,31,38,51,67,78,70,56,41,29,20,16,13)
for($i=0;$i -lt $vals1.Count-1;$i++){
  $x1=88+$i*52;$x2=88+($i+1)*52; $y1=440-$vals1[$i];$y2=440-$vals1[$i+1]; Add-Line $s $x1 $y1 $x2 $y2 $C.Violet 2 | Out-Null
  $z1=440-$vals2[$i];$z2=440-$vals2[$i+1]; Add-Line $s $x1 $z1 $x2 $z2 $C.Green 2 | Out-Null
}
Add-Text $s '定位分数' 705 350 82 18 11 $C.Violet 'Microsoft YaHei' -1 1 | Out-Null
Add-Text $s '编辑效果' 793 350 82 18 11 $C.Green 'Microsoft YaHei' -1 1 | Out-Null
Add-Note $s '[Sources] 本地结果台账结构；后续可视分析需求。'

# 24 roadmap
$s=New-Slide 24
Add-Title $s '工作计划：先补齐证据，再完成知识增强编辑闭环' 'ROADMAP'
$road=@(
 @('阶段 1','补齐候选层真实实验','19组合覆盖、失败层重跑',$C.Blue),@('阶段 2','完成统计与消融','11公式、Top-K、显著性',$C.Violet),
 @('阶段 3','构建知识子图','实体对齐与证据追踪',$C.TealDark),@('阶段 4','双路径编辑系统','参数记忆 + 图谱检索',$C.Green),@('阶段 5','可视分析与论文','解释、复现、对比结论',$C.Orange)
)
for($i=0;$i -lt 5;$i++){
  $x=58+$i*172; Add-Circle $s ([string]($i+1)) ($x+52) 145 40 $road[$i][3] | Out-Null
  if($i -lt 4){Add-FlowArrow $s ($x+100) 165 62}
  Add-Box $s $road[$i][0] $x 214 145 34 $road[$i][3] $road[$i][3] 13 $C.White 0 -1 2 | Out-Null
  Add-Box $s ($road[$i][1]+"`n"+$road[$i][2]) $x 252 145 98 $C.White $road[$i][3] 13 $C.Ink 0 -1 2 | Out-Null
}
Add-Box $s '最终目标' 58 408 120 40 $C.Dark $C.Dark 14 $C.White 0 -1 2 | Out-Null
Add-Text $s '证明定位方法能更高效地命中高性能编辑层，并将其转化为可控、可解释、可复现的知识增强视觉语言模型编辑框架。' 195 406 700 58 15 $C.Ink 'Microsoft YaHei' -1 1 | Out-Null
Add-Note $s '[Sources] 完整任务安排；实验结果台账；mywork-通用版.docx。'

$pres.SaveAs($out,24)
$pres.Export($renderDir,'PNG',1920,1080)
$slideCount=$pres.Slides.Count
$pres.Close(); $pp.Quit()
[System.Runtime.Interopservices.Marshal]::ReleaseComObject($pres) | Out-Null
[System.Runtime.Interopservices.Marshal]::ReleaseComObject($pp) | Out-Null
[GC]::Collect(); [GC]::WaitForPendingFinalizers()
Write-Output "OUT=$out"
Write-Output "SLIDES=$slideCount"
Write-Output "RENDER=$renderDir"
