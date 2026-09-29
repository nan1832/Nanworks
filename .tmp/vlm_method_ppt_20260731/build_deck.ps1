$ErrorActionPreference = 'Stop'

$FinalPptx = 'D:\开题\正式开题\Model Edit\bli2-reasonvqa\dataset\outputs\知识图谱增强视觉语言模型编辑_方法与后续工作_可编辑版.pptx'
$RenderDir = 'D:\开题\正式开题\Model Edit\bli2-reasonvqa\dataset\.tmp\vlm_method_ppt_20260731\rendered'

$ppLayoutBlank = 12
$ppSaveAsOpenXMLPresentation = 24
$msoTextOrientationHorizontal = 1
$msoFalse = 0
$msoTrue = -1
$msoShapeRectangle = 1
$msoShapeRoundedRectangle = 5
$msoShapeOval = 9
$msoShapeRightArrow = 33
$msoShapeChevron = 52
$msoAnchorTop = 1
$msoAnchorMiddle = 3
$ppAlignLeft = 1
$ppAlignCenter = 2
$ppAlignRight = 3

function RGBHex([string]$hex) {
    $h = $hex.TrimStart('#')
    $r = [Convert]::ToInt32($h.Substring(0,2),16)
    $g = [Convert]::ToInt32($h.Substring(2,2),16)
    $b = [Convert]::ToInt32($h.Substring(4,2),16)
    return $r + 256*$g + 65536*$b
}

$C = @{
    Ink      = RGBHex '#111827'
    Muted    = RGBHex '#4B5563'
    Light    = RGBHex '#F3F4F6'
    Rule     = RGBHex '#D1D5DB'
    Blue     = RGBHex '#2563EB'
    BlueLite = RGBHex '#DBEAFE'
    Teal     = RGBHex '#0F766E'
    TealLite = RGBHex '#CCFBF1'
    Orange   = RGBHex '#EA580C'
    OrangeLite = RGBHex '#FFEDD5'
    Green    = RGBHex '#15803D'
    GreenLite= RGBHex '#DCFCE7'
    Red      = RGBHex '#B91C1C'
    RedLite  = RGBHex '#FEE2E2'
    Purple   = RGBHex '#7C3AED'
    PurpleLite = RGBHex '#EDE9FE'
    White    = RGBHex '#FFFFFF'
    GrayBlue = RGBHex '#E8EEF8'
}

function Add-Text($slide, [string]$text, [double]$x, [double]$y, [double]$w, [double]$h,
                  [double]$fontSize = 18, [bool]$bold = $false, [int]$color = $C.Ink,
                  [int]$align = $ppAlignLeft, [int]$vAlign = $msoAnchorTop,
                  [string]$name = '') {
    $sh = $slide.Shapes.AddTextbox($msoTextOrientationHorizontal, $x, $y, $w, $h)
    if ($name) { $sh.Name = $name }
    $sh.Line.Visible = $msoFalse
    $sh.Fill.Visible = $msoFalse
    $sh.TextFrame2.MarginLeft = 0
    $sh.TextFrame2.MarginRight = 0
    $sh.TextFrame2.MarginTop = 0
    $sh.TextFrame2.MarginBottom = 0
    $sh.TextFrame2.WordWrap = $msoTrue
    $sh.TextFrame2.AutoSize = 0
    $sh.TextFrame2.VerticalAnchor = $vAlign
    $sh.TextFrame2.TextRange.Text = $text
    $sh.TextFrame2.TextRange.Font.Name = 'Microsoft YaHei'
    $sh.TextFrame2.TextRange.Font.NameFarEast = 'Microsoft YaHei'
    $sh.TextFrame2.TextRange.Font.Size = $fontSize
    $sh.TextFrame2.TextRange.Font.Bold = $(if($bold){$msoTrue}else{$msoFalse})
    $sh.TextFrame2.TextRange.Font.Fill.ForeColor.RGB = $color
    $sh.TextFrame2.TextRange.ParagraphFormat.Alignment = $align
    return $sh
}

function Add-Box($slide, [string]$text, [double]$x, [double]$y, [double]$w, [double]$h,
                 [int]$fill = $C.Light, [int]$line = $C.Rule, [double]$fontSize = 17,
                 [bool]$bold = $false, [int]$textColor = $C.Ink, [string]$name = '') {
    $sh = $slide.Shapes.AddShape($msoShapeRoundedRectangle, $x, $y, $w, $h)
    if ($name) { $sh.Name = $name }
    $sh.Fill.ForeColor.RGB = $fill
    $sh.Line.ForeColor.RGB = $line
    $sh.Line.Weight = 1
    $sh.TextFrame2.MarginLeft = 10
    $sh.TextFrame2.MarginRight = 10
    $sh.TextFrame2.MarginTop = 5
    $sh.TextFrame2.MarginBottom = 5
    $sh.TextFrame2.WordWrap = $msoTrue
    $sh.TextFrame2.VerticalAnchor = $msoAnchorMiddle
    $sh.TextFrame2.TextRange.Text = $text
    $sh.TextFrame2.TextRange.Font.Name = 'Microsoft YaHei'
    $sh.TextFrame2.TextRange.Font.NameFarEast = 'Microsoft YaHei'
    $sh.TextFrame2.TextRange.Font.Size = $fontSize
    $sh.TextFrame2.TextRange.Font.Bold = $(if($bold){$msoTrue}else{$msoFalse})
    $sh.TextFrame2.TextRange.Font.Fill.ForeColor.RGB = $textColor
    $sh.TextFrame2.TextRange.ParagraphFormat.Alignment = $ppAlignCenter
    return $sh
}

function Add-Arrow($slide, [double]$x, [double]$y, [double]$w, [double]$h, [int]$color = $C.Blue) {
    $a = $slide.Shapes.AddShape($msoShapeRightArrow, $x, $y, $w, $h)
    $a.Fill.ForeColor.RGB = $color
    $a.Line.Visible = $msoFalse
    return $a
}

function Add-Rule($slide, [double]$x1, [double]$y1, [double]$x2, [double]$y2, [int]$color = $C.Rule, [double]$weight = 1) {
    $l = $slide.Shapes.AddLine($x1,$y1,$x2,$y2)
    $l.Line.ForeColor.RGB = $color
    $l.Line.Weight = $weight
    return $l
}

function Set-WhiteBackground($slide) {
    try {
        $slide.FollowMasterBackground = $msoFalse
        $slide.Background.Fill.Solid()
        $slide.Background.Fill.ForeColor.RGB = $C.White
    } catch {
        # A new blank presentation is white by default.
    }
}

function Add-Title($slide, [string]$title, [string]$section, [int]$page) {
    Add-Text $slide $section 36 22 260 20 12 $true $C.Blue $ppAlignLeft $msoAnchorTop 'section-label' | Out-Null
    Add-Text $slide $title 36 48 890 52 35 $true $C.Ink $ppAlignLeft $msoAnchorTop 'slide-title' | Out-Null
    Add-Rule $slide 36 108 924 108 $C.Rule 1 | Out-Null
    Add-Text $slide ('{0:D2}' -f $page) 890 505 34 18 11 $false $C.Muted $ppAlignRight $msoAnchorTop 'page-number' | Out-Null
}

function Add-Notes($slide, [string[]]$sources, [string[]]$talk = @()) {
    $txt = ''
    if ($talk.Count -gt 0) {
        $txt += "讲解提示：`r`n" + (($talk | ForEach-Object { '• ' + $_ }) -join "`r`n") + "`r`n`r`n"
    }
    $txt += "[Sources]`r`n" + (($sources | ForEach-Object { '- ' + $_ }) -join "`r`n")
    try {
        $slide.NotesPage.Shapes.Placeholders.Item(2).TextFrame.TextRange.Text = $txt
    } catch {
        # Notes are helpful but should not block deck creation.
    }
}

function Add-Bullets($slide, [string[]]$items, [double]$x, [double]$y, [double]$w, [double]$h, [double]$fontSize = 18, [int]$color = $C.Ink) {
    $text = ($items | ForEach-Object { '• ' + $_ }) -join "`r`n"
    $sh = Add-Text $slide $text $x $y $w $h $fontSize $false $color
    $sh.TextFrame2.TextRange.ParagraphFormat.SpaceAfter = 8
    return $sh
}

function Add-MethodSlide($pres, [int]$page, [string]$title, [string]$methodId, [string[]]$principles,
                         [string[]]$flow, [string]$top3, [string]$perf, [string]$caveat,
                         [int]$accent, [int]$accentLite, [string[]]$sources) {
    $s = $pres.Slides.Add($pres.Slides.Count + 1, $ppLayoutBlank)
    Set-WhiteBackground $s
    Add-Title $s $title 'STEP 1 · 层定位方法' $page

    Add-Text $s $methodId 38 132 300 28 19 $true $accent | Out-Null
    Add-Bullets $s $principles 38 174 300 210 18 $C.Ink | Out-Null

    $n = $flow.Count
    $startX = 380
    $nodeW = 124
    $gap = 22
    $y = 165
    for ($i=0; $i -lt $n-1; $i++) {
        Add-Arrow $s ($startX + $nodeW + $i*($nodeW+$gap) + 2) ($y+34) ($gap-4) 18 $accent | Out-Null
    }
    for ($i=0; $i -lt $n; $i++) {
        $fill = if($i -eq $n-1){$accentLite}else{$C.Light}
        $line = if($i -eq $n-1){$accent}else{$C.Rule}
        Add-Box $s $flow[$i] ($startX + $i*($nodeW+$gap)) $y $nodeW 86 $fill $line 16 ($i -eq $n-1) $C.Ink ('flow-node-'+$i) | Out-Null
    }

    Add-Text $s '统一案例：MMKE-visual × Qwen2.5-VL-3B' 380 286 520 24 16 $true $C.Muted | Out-Null
    Add-Box $s ('Top-3：' + $top3) 380 322 245 58 $accentLite $accent 20 $true $accent 'result-top3' | Out-Null
    Add-Box $s $perf 645 322 245 58 $C.Light $C.Rule 17 $true $C.Ink 'result-performance' | Out-Null
    Add-Text $s ('解释边界：' + $caveat) 380 400 510 72 16 $false $C.Muted | Out-Null

    Add-Notes $s $sources @('先讲信号来自哪里，再讲为什么该层会进入 Top-K。','定位结果必须经过同配置真实编辑训练与独立 test/eval 验证。')
    return $s
}

function HeatColor([double]$v, [double]$min, [double]$max, [bool]$higherBetter = $true) {
    if ($max -le $min) { return $C.Light }
    $t = ($v-$min)/($max-$min)
    if(-not $higherBetter){$t=1-$t}
    if($t -ge 0.75){return RGBHex '#BBF7D0'}
    if($t -ge 0.50){return RGBHex '#DCFCE7'}
    if($t -ge 0.25){return RGBHex '#FEF3C7'}
    return RGBHex '#FEE2E2'
}

$ppt = New-Object -ComObject PowerPoint.Application
$ppt.Visible = $msoTrue
$pres = $ppt.Presentations.Add()
$pres.PageSetup.SlideWidth = 960
$pres.PageSetup.SlideHeight = 540

$srcDoc = 'C:\Users\zhoun\Desktop\mywork\实验说明\mywork-通用版.docx'
$methodDoc = 'D:\开题\正式开题\Model Edit\bli2-reasonvqa\dataset\md\Location\6edit_layer_localization_candidate_methods_简洁说明版.md'
$outcomeDoc = 'D:\开题\正式开题\Model Edit\bli2-reasonvqa\dataset\md\Location\6location_7model_3datas_top_3_5_layers_outcome.md'
$analysisDir = 'D:\开题\正式开题\Model Edit\bli2-reasonvqa\dataset\md\Location\VisualGradient_11formula_analysis_files_20260720\analysis_outputs_20260731'

# 1. Cover
$s = $pres.Slides.Add(1,$ppLayoutBlank)
Set-WhiteBackground $s
Add-Text $s '知识图谱增强的视觉语言模型编辑' 40 34 620 28 17 $true $C.Blue | Out-Null
Add-Text $s '从层定位，到关联知识泛化' 40 154 820 142 52 $true $C.Ink $ppAlignLeft $msoAnchorMiddle | Out-Null
Add-Text $s '7 种定位策略 · 真实编辑验证 · 知识子图双路注入 · 交互式分析' 40 326 820 42 22 $false $C.Muted | Out-Null
Add-Rule $s 40 402 920 402 $C.Rule 1.2 | Out-Null
Add-Text $s '方法讲解与后续工作  |  实验快照：2026-07-31' 40 428 550 26 16 $false $C.Muted | Out-Null
Add-Text $s '汇报人：________' 704 428 216 26 16 $false $C.Muted $ppAlignRight | Out-Null
Add-Notes $s @($srcDoc,$methodDoc,$outcomeDoc) @('开场先给出完整主张：先确定可编辑层，再让知识修改沿图谱传播。')

# 2. Problem
$s = $pres.Slides.Add(2,$ppLayoutBlank); Set-WhiteBackground $s
Add-Title $s '只改“目标事实”，仍可能留下关联知识冲突' '研究问题' 2
Add-Text $s '现有 VLM 编辑的缺口' 38 138 300 30 22 $true $C.Red | Out-Null
Add-Bullets $s @('目标答案可以被改对，但关联问答仍沿用旧知识。','知识分散在多层跨模态表征中，编辑位置不可直接观察。','需要同时回答“改哪里、注入什么、如何验证副作用”。') 38 184 300 220 18 | Out-Null
Add-Arrow $s 355 252 44 20 $C.Red | Out-Null
Add-Arrow $s 566 252 44 20 $C.Orange | Out-Null
Add-Arrow $s 772 252 44 20 $C.Blue | Out-Null
Add-Box $s "旧事实`r`n詹姆斯 → 湖人" 402 210 150 104 $C.RedLite $C.Red 18 $true $C.Red | Out-Null
Add-Box $s "目标编辑`r`n球队 → 热火" 612 210 150 104 $C.OrangeLite $C.Orange 18 $true $C.Orange | Out-Null
Add-Box $s "应同步变化`r`n工作地点 → 迈阿密" 818 210 106 104 $C.BlueLite $C.Blue 16 $true $C.Blue | Out-Null
Add-Text $s '核心研究问题：如何在保持局部性的同时，让一次编辑对相关知识产生正确、可解释、可验证的传播？' 355 374 569 78 22 $true $C.Ink | Out-Null
Add-Notes $s @($srcDoc + '，§研究背景、§研究问题') @('用球队与工作地点的例子说明“目标知识成功”不等于“关联知识一致”。')

# 3. Full pipeline
$s = $pres.Slides.Add(3,$ppLayoutBlank); Set-WhiteBackground $s
Add-Title $s '完整任务是一条“定位—编辑—验证—诊断”闭环' '总体方案' 3
$xs = @(42,190,338,486,634,782)
for($i=0;$i -lt 5;$i++){Add-Arrow $s ($xs[$i]+124) 234 20 18 $(if($i -eq 0){$C.Blue}else{$C.Teal}) | Out-Null}
$steps = @(
    @('1  层定位','7 种方法输出 Top-K'),
    @('2  真实扫层','同配置训练＋独立评测'),
    @('3  子图构建','实体链接＋受限扩展'),
    @('4  子图编码','RGCN 聚合关联知识'),
    @('5  双路注入','目标知识＋相关知识'),
    @('6  可视分析','指标、热图、问答诊断')
)
for($i=0;$i -lt $steps.Count;$i++){
    $fill=if($i -eq 0){$C.BlueLite}else{$C.Light}; $line=if($i -eq 0){$C.Blue}else{$C.Rule}
    Add-Box $s ($steps[$i][0]+"`r`n"+$steps[$i][1]) $xs[$i] 194 124 98 $fill $line 16 ($i -eq 0) $C.Ink | Out-Null
}
Add-Text $s '定位是第一步，不是最终贡献' 42 348 350 34 24 $true $C.Blue | Out-Null
Add-Text $s 'Top-K 只回答“值得在哪里训练”；论文最终要证明的是：在选定层注入结构化关联知识后，可靠性、泛化性与局部性形成更优平衡。' 42 396 850 62 19 $false $C.Ink | Out-Null
Add-Notes $s @($srcDoc + '，§5.3整体流程、§5.3.4–5.3.7',$methodDoc + '，§8统一执行流程') @('突出蓝色第一步只是入口，后续四个模块才构成完整方法。')

# 4. Scope & protocol
$s = $pres.Slides.Add(4,$ppLayoutBlank); Set-WhiteBackground $s
Add-Title $s '统一实验协议把“候选层好不好”变成可比较证据' '实验设计' 4
Add-Rule $s 329 148 329 454 $C.Rule 1 | Out-Null; Add-Rule $s 634 148 634 454 $C.Rule 1 | Out-Null
Add-Text $s '3 个数据集' 42 142 250 28 22 $true $C.Blue | Out-Null
Add-Bullets $s @('EVQA-pilot500：编辑可靠性、泛化性、局部性','MMKE-visual：视觉知识编辑','MMKE-entity：实体知识编辑') 42 188 250 190 17 | Out-Null
Add-Text $s '7 个模型' 350 142 250 28 22 $true $C.Teal | Out-Null
Add-Bullets $s @('BLIP2、InstructBLIP','MiniGPT-4、LLaVA','PaliGemma、SmolVLM','Qwen2.5-VL') 350 188 240 210 17 | Out-Null
Add-Text $s '一套验收标准' 656 142 250 28 22 $true $C.Orange | Out-Null
Add-Bullets $s @('候选并集逐层训练 50 epoch','按最小 EMA loss 选 checkpoint','只用对应 test/eval 数据评测','双标记：selected_checkpoint.tsv + eval_full.done','比较 Best@K、Mean@K、Regret@K、相关性') 656 188 250 236 17 | Out-Null
Add-Text $s '可比性的关键：同一数据、同一训练配置、同一评测口径；定位方法只改变候选层排序。' 42 466 864 28 18 $true $C.Ink | Out-Null
Add-Notes $s @($srcDoc + '，§5.3.1、§5.3.6',$methodDoc + '，§0统一实验定义、§7定位评价、§8统一执行流程',$outcomeDoc + '，§4服务器结构化结果总表')

# 5. Taxonomy
$s = $pres.Slides.Add(5,$ppLayoutBlank); Set-WhiteBackground $s
Add-Title $s '7 种方法从“结构先验”走向“视觉梯度与因果证据”' '定位方法全景' 5
$rows = @(
    @('Middle','网络深度','距中点最近','Direct'),
    @('VisEdit','关键 token 贡献','高贡献区之前','Pre'),
    @('SaLEM','MLP 参数绝对梯度','显著性最高','Direct'),
    @('LGA','新旧参数梯度内积','协同更新最强','Direct'),
    @('Perturb-KL','视觉 token 扰动','KL 最敏感','Direct'),
    @('CMA','污染—恢复','因果恢复最高','Direct'),
    @('Ours','新旧视觉梯度关系','11 公式排序','Direct')
)
$tbl = $s.Shapes.AddTable(8,4,42,142,876,310).Table
$heads=@('方法','定位信号','候选规则','插入位置')
for($col=1;$col -le 4;$col++){$tbl.Cell(1,$col).Shape.TextFrame.TextRange.Text=$heads[$col-1]}
for($r=0;$r -lt $rows.Count;$r++){for($col=0;$col -lt 4;$col++){$tbl.Cell($r+2,$col+1).Shape.TextFrame.TextRange.Text=$rows[$r][$col]}}
for($r=1;$r -le 8;$r++){
 for($col=1;$col -le 4;$col++){
  $cell=$tbl.Cell($r,$col).Shape; $cell.TextFrame.MarginLeft=7; $cell.TextFrame.MarginRight=7
  $cell.TextFrame2.TextRange.Font.Name='Microsoft YaHei'; $cell.TextFrame2.TextRange.Font.NameFarEast='Microsoft YaHei'; $cell.TextFrame2.TextRange.Font.Size=16
  $cell.TextFrame2.TextRange.Font.Fill.ForeColor.RGB=$C.Ink
  try {
    $cell.Fill.Solid()
    $cell.Fill.ForeColor.RGB=$(if($r -eq 1){$C.Ink}elseif($r -eq 8){$C.BlueLite}else{$C.White})
  } catch {}
  if($r -eq 1){$cell.TextFrame2.TextRange.Font.Fill.ForeColor.RGB=$C.White;$cell.TextFrame2.TextRange.Font.Bold=$msoTrue}
  try {$cell.Line.ForeColor.RGB=$C.Rule} catch {}
 }
}
Add-Text $s '注：Perturb-KL-Pre-AltSeq 仅作为前置插入消融，不计入 7 个正式策略。' 42 470 876 26 16 $false $C.Muted | Out-Null
Add-Notes $s @($methodDoc + '，§0.6主方法与候选规则、§10主实验默认配置')

# 6–12 Method slides
Add-MethodSlide $pres 6 'Middle：用网络中点作为零成本结构先验' 'Middle-Prior-Direct' `
 @('不依赖数据与梯度，适合作为最低成本基线。','严格中点 ρ=0.5，按到中点的距离排序。','候选层直接挂载 adapter，不做层位偏移。') `
 @('读取层数 N','计算网络中点','按距离排序','输出 Direct Top-K') `
 'L17, L18, L16' 'Best@3 70.65  |  Mean@3 70.02' '它检验“中层先验”是否已足够，不能反映样本级编辑信号。' $C.Blue $C.BlueLite @($methodDoc+'，§1 Middle-layer Prior',$analysisDir+'\baseline_candidates.csv',$analysisDir+'\accepted_outcome_rows.csv') | Out-Null

Add-MethodSlide $pres 7 'VisEdit：高贡献区之前更适合注入视觉编辑信号' 'VisEdit-Contrib-Pre-KeyToken' `
 @('对目标关键 token 的预测做模块输出归因。','联合 Attention/MLP 映射概率与归一化 logit。','先识别高贡献区，再选择其前置层挂载 adapter。') `
 @('抽取 key token','计算模块贡献','平滑并识别高贡献区','向前偏移输出 Top-K') `
 'L28, L27, L26' 'Best@3 68.35  |  Mean@3 68.24' '严格 KeyToken 才是主表；历史 FirstToken 只能作为诊断。' $C.Purple $C.PurpleLite @($srcDoc+'，§5.3.2模块输出归因',$methodDoc+'，§2 VisEdit-Contrib-Pre',$analysisDir+'\baseline_candidates.csv') | Out-Null

Add-MethodSlide $pres 8 'SaLEM：参数绝对梯度揭示“最容易被新知识推动”的层' 'SaLEM-Alt-Direct' `
 @('以完整 alt 序列损失反向传播。','仅比较统一的 MLP/FFN 参数集合。','参数→列→矩阵→层逐级聚合绝对梯度。') `
 @('计算 alt loss','提取 MLP 参数梯度','逐级聚合显著性','直接选显著层 Top-K') `
 'L12, L11, L14' 'Best@3 71.00  |  Mean@3 70.61' '这是 SaLEM 风格定位基线，不声称复现完整编辑器。' $C.Teal $C.TealLite @($methodDoc+'，§3 SaLEM-Based Salient-Layer Selection',$analysisDir+'\baseline_candidates.csv',$analysisDir+'\accepted_outcome_rows.csv') | Out-Null

Add-MethodSlide $pres 9 'LGA：新旧知识梯度同向时，该层更可能是“黄金层”' 'LGA-Param-Direct-AltModelPred' `
 @('旧知识来自冻结模型的 model_pred，新知识来自 alt。','分别计算 MLP/FFN weight 的新旧参数梯度。','用每层 raw gradient dot 衡量共同承载程度。') `
 @('生成旧/新目标','求两组参数梯度','计算层内梯度内积','直接选 dot 最大 Top-K') `
 'L2, L30, L1' 'Best@3 69.93  |  Mean@3 68.82' '主版本是参数梯度；hidden-state 变体不能冒充原始 LGA。' $C.Orange $C.OrangeLite @($methodDoc+'，§4 GoldenLayer / Layer Gradient Analysis',$analysisDir+'\baseline_candidates.csv') | Out-Null

Add-MethodSlide $pres 10 'Perturb-KL：视觉表征被扰动后，输出变化越大越关键' 'Perturb-KL-Direct-AltSeq' `
 @('只扰动 visual tokens，保持文本与目标序列不变。','多噪声尺度、多随机种子比较 clean/perturbed 分布。','在完整 alt 序列上聚合稳健 KL 分数。') `
 @('注入视觉噪声','获得 clean/perturbed 分布','多尺度多种子稳健聚合','直接选 KL 敏感 Top-K') `
 'L0, L13, L14' 'Best@3 70.42  |  Mean@3 70.21' '这是本文构造的序列级敏感性基线；Pre 版本仅为消融。' $C.Red $C.RedLite @($methodDoc+'，§5 Perturb-KL-Direct',$analysisDir+'\baseline_candidates.csv') | Out-Null

Add-MethodSlide $pres 11 'CMA：恢复某层视觉状态能挽救答案，才构成因果证据' 'CMA-Direct' `
 @('先确认视觉污染确实降低目标答案支持。','逐层恢复 clean visual hidden state。','以恢复后的目标支持提升 CR 作为主分数。') `
 @('计算 clean 支持','污染视觉输入','逐层恢复 clean 状态','按 CR 选 Top-K') `
 'L1, L0, L6' 'Best@3 70.42  |  Mean@3 70.02' '该案例 coverage=31/214（14.5%），需低覆盖标记；因果恢复不等于真实可编辑性。' $C.Green $C.GreenLite @($methodDoc+'，§6.5 CMA-Direct / Visual Causal Restoration',$analysisDir+'\baseline_candidates.csv') | Out-Null

Add-MethodSlide $pres 12 'Ours：用新旧知识的视觉梯度关系直接预测可编辑层' 'Ours-VisualGradient-Direct' `
 @('在每层 visual-token hidden state 上插入零扰动。','分别求旧知识 model_pred 与新知识 alt 的视觉梯度。','7 个基础公式＋4 个深度加权指标并行输出 Top-K。') `
 @('对齐旧/新目标','提取视觉隐藏梯度','计算 11 个候选公式','直接输出公式级 Top-K') `
 'L0, L1, L2' 'Best@3 70.42  |  Mean@3 69.94' '当前主候选 M_abscos_x_newn = |cos| × new_norm；仍是暂定主公式。' $C.Blue $C.BlueLite @($methodDoc+'，§6 Ours-VisualGradient-Direct',$analysisDir+'\formula_topk_all_21.csv',$analysisDir+'\formula_global_summary.csv') | Out-Null

# 13. Layer heatmap
$s=$pres.Slides.Add(13,$ppLayoutBlank);Set-WhiteBackground $s
Add-Title $s '同一模型上，7 种方法给出的候选层高度分散' '定位结果热力图' 13
$methodRows=@(
 @('Middle',@(17,18,16)),@('VisEdit',@(28,27,26)),@('SaLEM',@(12,11,14)),@('LGA',@(2,30,1)),@('Perturb-KL',@(0,13,14)),@('CMA',@(1,0,6)),@('Ours',@(0,1,2))
)
$gx=178;$gy=162;$cw=20.5;$rh=38
for($l=0;$l -le 34;$l++){Add-Text $s ([string]$l) ($gx+$l*$cw) 132 $cw 18 10 $false $C.Muted $ppAlignCenter | Out-Null}
for($r=0;$r -lt $methodRows.Count;$r++){
 Add-Text $s $methodRows[$r][0] 42 ($gy+$r*$rh+7) 126 22 16 ($methodRows[$r][0] -eq 'Ours') $(if($methodRows[$r][0] -eq 'Ours'){$C.Blue}else{$C.Ink}) | Out-Null
 $sel=$methodRows[$r][1]
 for($l=0;$l -le 34;$l++){
  $idx=[Array]::IndexOf($sel,$l)
  $fill=if($idx -eq 0){$C.Blue}elseif($idx -eq 1){RGBHex '#60A5FA'}elseif($idx -eq 2){RGBHex '#BFDBFE'}else{$C.Light}
  Add-Box $s '' ($gx+$l*$cw) ($gy+$r*$rh) ($cw-2) 24 $fill $fill 10 $false $C.Ink | Out-Null
 }
}
Add-Text $s '颜色表示 Top-1 / Top-2 / Top-3 排名；案例为 MMKE-visual × Qwen2.5-VL-3B。' 178 446 716 22 16 $false $C.Muted | Out-Null
Add-Text $s '含义：候选层并不由“模型深度”单独决定；不同信号捕捉的是结构先验、参数可塑性、扰动敏感性、因果恢复或视觉梯度关系。' 42 478 852 40 17 $true $C.Ink | Out-Null
Add-Notes $s @($analysisDir+'\baseline_candidates.csv',$analysisDir+'\formula_topk_all_21.csv')

# 14. Formula ablation heatmap
$s=$pres.Slides.Add(14,$ppLayoutBlank);Set-WhiteBackground $s
Add-Title $s '11 公式消融：|cos| × new_norm 的平均相关性最高' 'Ours 公式消融' 14
$formulaRows=@(
 @('M_abscos_x_newn','B7',0.323,'15/18',9,68.49,65.58,2.29),
 @('M_new_norm','B7',0.320,'13/18',10,69.16,66.51,2.24),
 @('M_newn_x_1mcos','B7',0.308,'13/18',10,65.23,63.80,6.17),
 @('M_pos_ratio','B7',0.145,'12/18',5,74.00,67.34,2.88),
 @('Ours-AbsDirection','O4',0.090,'12/18',13,70.22,68.56,3.88),
 @('Ours-Direct-Conflict','O4',0.088,'3/5',2,71.33,68.58,2.13),
 @('M_cos','B7',0.072,'12/18',4,59.67,58.67,13.26),
 @('M_dot','B7',0.068,'12/18',8,67.48,65.14,4.18),
 @('Ours-NoDirection','O4',0.032,'10/18',13,70.10,67.90,4.00),
 @('Ours-1MinusCos','O4',0.016,'10/18',13,70.08,67.29,4.02),
 @('M_conflict','B7',-0.068,'6/18',3,62.18,59.00,8.25)
)
$headers=@('公式','族','ρ','正相关','完整N','Best@3','Mean@3','Regret↓')
$x=@(42,220,286,382,466,560,650,740);$w=@(174,62,92,80,90,86,86,92)
for($i=0;$i -lt $headers.Count;$i++){Add-Box $s $headers[$i] $x[$i] 128 $w[$i] 28 $C.Ink $C.Ink 16 $true $C.White | Out-Null}
for($r=0;$r -lt $formulaRows.Count;$r++){
 $y=160+$r*29
 $row=$formulaRows[$r]
 $isPrimary=$row[0] -eq 'M_abscos_x_newn'
 $vals=@($row[0],$row[1],('{0:N3}' -f $row[2]),$row[3],$row[4],('{0:N2}' -f $row[5]),('{0:N2}' -f $row[6]),('{0:N2}' -f $row[7]))
 for($col=0;$col -lt $vals.Count;$col++){
  $fill=$C.White
  if($col -eq 2){$fill=HeatColor ([double]$row[2]) -0.068 0.323 $true}
  elseif($col -eq 4){$fill=HeatColor ([double]$row[4]) 2 13 $true}
  elseif($col -eq 5){$fill=HeatColor ([double]$row[5]) 59 74 $true}
  elseif($col -eq 6){$fill=HeatColor ([double]$row[6]) 58 69 $true}
  elseif($col -eq 7){$fill=HeatColor ([double]$row[7]) 2 13.3 $false}
  elseif($isPrimary){$fill=$C.BlueLite}
  Add-Box $s ([string]$vals[$col]) $x[$col] $y $w[$col] 26 $fill $C.Rule 16 $(if($col -eq 0 -and $isPrimary){$true}else{$false}) $(if($isPrimary -and $col -eq 0){$C.Blue}else{$C.Ink}) | Out-Null
 }
}
Add-Text $s 'B7=7个基础公式，O4=4个深度加权指标。M_abscos 与 M_new_norm 很接近；前者暂定为主公式，因为平均 Spearman 最高（0.323，15/18 为正）。' 42 485 876 36 16 $true $C.Ink | Out-Null
Add-Notes $s @($analysisDir+'\formula_global_summary.csv',$analysisDir+'\visual_gradient_formula_evidence_report.md')

# 15. Global comparison
$s=$pres.Slides.Add(15,$ppLayoutBlank);Set-WhiteBackground $s
Add-Title $s 'Ours 平均优于 6 个基线，但证据尚未达到统计显著' '7 方法综合比较' 15
$pairRows=@(
 @('Middle',2.662,0.601,'6/0/3',0.508,9),
 @('VisEdit',4.133,1.795,'5/0/4',1.000,6),
 @('SaLEM',2.792,1.341,'6/0/3',0.508,9),
 @('LGA',1.284,2.345,'6/1/2',0.289,9),
 @('Perturb-KL',4.021,2.771,'3/5/1',0.625,9),
 @('CMA',3.538,2.960,'4/3/2',0.688,4)
)
$heads=@('方法','ΔBest@3','ΔMean@3','W/T/L','p','严格 N')
$tx=@(42,190,390,590,704,812);$tw=@(144,196,196,110,104,106)
for($i=0;$i -lt $heads.Count;$i++){Add-Box $s $heads[$i] $tx[$i] 140 $tw[$i] 38 $C.Ink $C.Ink 16 $true $C.White | Out-Null}
for($r=0;$r -lt $pairRows.Count;$r++){
 $y=182+$r*46;$row=$pairRows[$r]
 $values=@($row[0],('{0:+0.000;-0.000;0.000}' -f $row[1]),('{0:+0.000;-0.000;0.000}' -f $row[2]),$row[3],('{0:N3}' -f $row[4]),$row[5])
 for($col=0;$col -lt $values.Count;$col++){
  $fill=if($col -eq 1){HeatColor ([double]$row[1]) 1.2 4.2 $true}elseif($col -eq 2){HeatColor ([double]$row[2]) 0.5 3.0 $true}elseif($col -eq 4){$C.OrangeLite}else{$C.White}
  Add-Box $s ([string]$values[$col]) $tx[$col] $y $tw[$col] 40 $fill $C.Rule 16 ($col -eq 0) $C.Ink | Out-Null
 }
}
Add-Text $s '表中正值表示 Ours 更好。6 组比较的平均 ΔBest@3 与 ΔMean@3 均为正；但所有双侧符号检验 p≥0.289，因此只能称为“描述性优势”，不能声称显著胜出。' 42 470 876 48 16 $true $C.Ink | Out-Null
Add-Notes $s @($analysisDir+'\baseline_pairwise_vs_M_abscos.csv',$analysisDir+'\visual_gradient_formula_evidence_report.md')

# 16. Evidence boundary
$s=$pres.Slides.Add(16,$ppLayoutBlank);Set-WhiteBackground $s
Add-Title $s '当前证据支持“有潜力”，尚不足以证明“稳定胜出”' '阶段结论' 16
Add-Text $s '已经得到的证据' 42 142 390 30 23 $true $C.Green | Out-Null
Add-Bullets $s @('21 个数据集×模型组合均生成 11 公式 Top-K。','M_abscos 平均 Spearman=0.323，15/18 组合为正。','对 6 个正式基线，平均 Best@3/Mean@3 改善均为正。','真实评测坚持 selected checkpoint + 独立 test/eval 双验收。') 42 188 390 224 18 | Out-Null
Add-Text $s '尚不能下的结论' 518 142 390 30 23 $true $C.Red | Out-Null
Add-Bullets $s @('不能称 Ours 已统计显著优于所有基线。','Top-3 完整结果目前仅覆盖 9/19 个 eligible 组合。','M_abscos 与 M_new_norm 差距很小，主公式仍需敏感性检验。','低 coverage 的 CMA 与历史 FirstToken 结果需单独标记。') 518 188 390 224 18 | Out-Null
Add-Box $s '论文口径：暂定主公式 + 完整补测 + 严格配对统计 + 失败层独立说明' 168 446 624 52 $C.BlueLite $C.Blue 20 $true $C.Blue | Out-Null
Add-Notes $s @($analysisDir+'\visual_gradient_formula_evidence_report.md',$outcomeDoc+'，§3.5.1异常原因、现存checkpoint与重跑建议')

# 17. KG subgraph
$s=$pres.Slides.Add(17,$ppLayoutBlank);Set-WhiteBackground $s
Add-Title $s '定位之后：用受限知识子图表示关联变化' 'STEP 2 · 关联知识建模' 17
$fx=@(42,218,394,570,746)
for($i=0;$i -lt 4;$i++){Add-Arrow $s ($fx[$i]+144) 244 24 18 $C.Teal | Out-Null}
$f=@("目标编辑三元组`r`n(s,r,o_new)","实体链接`r`n匹配外部知识图谱","受限 n-hop / m-neighbor`r`n扩展并抑噪","早层隐藏状态`r`n初始化实体与关系","RGCN/RGNN 编码`r`n得到关联知识向量")
for($i=0;$i -lt 5;$i++){Add-Box $s $f[$i] $fx[$i] 198 144 112 $(if($i -eq 4){$C.TealLite}else{$C.Light}) $(if($i -eq 4){$C.Teal}else{$C.Rule}) 16 ($i -eq 4) $C.Ink | Out-Null}
Add-Text $s '规模控制' 42 362 170 24 18 $true $C.Teal | Out-Null
Add-Text $s '最大阶数 n 与每个实体最大邻居数 m 控制子图大小；目标是保留与编辑事实相关的最小结构，而不是把整个图谱搬进模型。' 42 398 418 70 17 | Out-Null
Add-Text $s '表征对齐' 520 362 170 24 18 $true $C.Teal | Out-Null
Add-Text $s '实体/关系初始向量来自 VLM 早层隐藏状态，使外部图结构与当前图文语义处于可融合空间。' 520 398 388 70 17 | Out-Null
Add-Notes $s @($srcDoc+'，§5.3.4子图构建、§5.3.5子图编码')

# 18. Dual injection
$s=$pres.Slides.Add(18,$ppLayoutBlank);Set-WhiteBackground $s
Add-Title $s '双路注入让模型既记住目标事实，也吸收关联知识' 'STEP 3 · 知识编辑' 18
# Arrows first
Add-Arrow $s 202 210 36 18 $C.Blue | Out-Null; Add-Arrow $s 202 354 36 18 $C.Teal | Out-Null
Add-Arrow $s 474 210 36 18 $C.Blue | Out-Null; Add-Arrow $s 474 354 36 18 $C.Teal | Out-Null
Add-Arrow $s 698 282 36 18 $C.Orange | Out-Null
Add-Box $s "编辑样本`r`n(image, src, alt)" 42 174 160 92 $C.BlueLite $C.Blue 17 $true $C.Blue | Out-Null
Add-Box $s "关联知识子图`r`nG_sub" 42 318 160 92 $C.TealLite $C.Teal 17 $true $C.Teal | Out-Null
Add-Box $s "目标知识注入`r`nCross-Attention + IM`r`n按视觉区域调节强度" 238 158 236 124 $C.Light $C.Blue 17 $true $C.Ink | Out-Null
Add-Box $s "关联知识注入`r`nRGCN 表征与视觉特征融合" 238 310 236 106 $C.Light $C.Teal 17 $true $C.Ink | Out-Null
Add-Box $s '融合后的视觉表征' 510 246 188 88 $C.OrangeLite $C.Orange 19 $true $C.Orange | Out-Null
Add-Box $s "送入下一 LLM 层`r`n生成编辑后答案" 734 246 184 88 $C.Light $C.Rule 18 $true $C.Ink | Out-Null
Add-Text $s '训练目标：可靠性 ↑  ·  文本/模态泛化性 ↑  ·  文本/模态局部性保持  ·  KL 约束副作用' 80 456 800 32 18 $true $C.Ink $ppAlignCenter | Out-Null
Add-Notes $s @($srcDoc+'，§5.3.6知识编辑') @('IM 用提示最后一个 token 生成区域级编辑强度；图分支补充目标事实引起的关联变化。')

# 19. Interactive analysis
$s=$pres.Slides.Add(19,$ppLayoutBlank);Set-WhiteBackground $s
Add-Title $s '交互式可视分析把实验结果变成可诊断的编辑过程' 'STEP 4 · 可视分析' 19
$px=@(42,214,386,558,730)
for($i=0;$i -lt 4;$i++){Add-Arrow $s ($px[$i]+140) 244 24 18 $C.Purple | Out-Null}
$items=@(
 @('选择模型/数据','确定待编辑对象'),
 @('查看层贡献','比较 7 方法候选'),
 @('查看编辑指标','可靠性/泛化/局部性'),
 @('问答＋关联子图','验证知识传播'),
 @('注意力热图','发现注入偏移')
)
for($i=0;$i -lt 5;$i++){Add-Box $s ($items[$i][0]+"`r`n"+$items[$i][1]) $px[$i] 198 140 108 $(if($i -eq 4){$C.PurpleLite}else{$C.Light}) $(if($i -eq 4){$C.Purple}else{$C.Rule}) 16 ($i -eq 4) $C.Ink | Out-Null}
Add-Text $s '诊断闭环' 42 360 180 26 20 $true $C.Purple | Out-Null
Add-Text $s '当答案、关联子图与注意力区域不一致时，返回候选层、IM 强度或子图采样参数，形成“发现偏移—定位原因—重新训练”的迭代。' 42 404 840 62 18 | Out-Null
Add-Notes $s @($srcDoc+'，§5.3.7交互式编辑可视分析')

# 20. Next plan
$s=$pres.Slides.Add(20,$ppLayoutBlank);Set-WhiteBackground $s
Add-Title $s '下一步按“证据闭环”推进，不只继续堆扫层结果' '后续工作计划' 20
Add-Rule $s 82 286 878 286 $C.Ink 1.5 | Out-Null
$mx=@(96,280,464,648,832)
$dates=@('2026.08','2026.08–09','2026.09–11','2026.11–12','2027.01–05')
$titles=@('补齐定位证据','锁定最佳层','实现图谱模块','完成主实验','系统与论文')
$desc=@(
 "补齐 Top3/Top5 真实评测`r`n重算 strict KeyToken`r`n失败层分栏说明",
 "主/稳定版敏感性`r`n严格配对统计`r`n最佳层清单",
 "实体链接与受限扩展`r`nRGCN 编码`r`n子图规模/噪声消融",
 "目标＋关联双路注入`r`n三数据集统一评测`r`n三类指标对比",
 "交互式可视分析`r`n案例诊断与用户流程`r`n论文与复现实验归档"
)
for($i=0;$i -lt 5;$i++){
 Add-Box $s '' ($mx[$i]-7) 279 14 14 $(if($i -eq 0){$C.Blue}else{$C.Ink}) $(if($i -eq 0){$C.Blue}else{$C.Ink}) 8 $false $C.White | Out-Null
 Add-Text $s $dates[$i] ($mx[$i]-52) 245 104 22 16 $true $C.Muted $ppAlignCenter | Out-Null
 Add-Text $s $titles[$i] ($mx[$i]-72) 316 144 26 18 $true $(if($i -eq 0){$C.Blue}else{$C.Ink}) $ppAlignCenter | Out-Null
 Add-Text $s $desc[$i] ($mx[$i]-76) 354 152 96 16 $false $C.Muted $ppAlignCenter | Out-Null
}
Add-Box $s '阶段门槛：只有“候选层训练完成 + 独立评测完成 + 统计口径可复现”，才进入下一模块的正式结论。' 116 460 728 42 $C.BlueLite $C.Blue 17 $true $C.Blue | Out-Null
Add-Notes $s @($srcDoc+'，§6进度安排',$outcomeDoc+'，§3.5.1异常原因、现存checkpoint与重跑建议',$analysisDir+'\visual_gradient_formula_evidence_report.md')

# 21. Closing
$s=$pres.Slides.Add(21,$ppLayoutBlank);Set-WhiteBackground $s
Add-Text $s '核心结论' 42 42 280 24 16 $true $C.Blue | Out-Null
Add-Text $s "先把位置找对，`r`n再让一次编辑沿知识图谱正确传播" 42 146 780 128 44 $true $C.Ink | Out-Null
Add-Rule $s 42 324 918 324 $C.Rule 1 | Out-Null
Add-Text $s '定位贡献' 42 360 200 26 20 $true $C.Blue | Out-Null
Add-Text $s '7 种方法统一比较，视觉梯度公式提供数据驱动候选层。' 42 398 250 60 17 | Out-Null
Add-Text $s '编辑贡献' 354 360 200 26 20 $true $C.Teal | Out-Null
Add-Text $s '目标知识与关联知识双路注入，面向多跳泛化而非单题命中。' 354 398 250 60 17 | Out-Null
Add-Text $s '系统贡献' 666 360 200 26 20 $true $C.Purple | Out-Null
Add-Text $s '用指标、子图与注意力热图解释编辑效果和失败原因。' 666 398 250 60 17 | Out-Null
Add-Notes $s @($srcDoc,$methodDoc,$analysisDir+'\visual_gradient_formula_evidence_report.md') @('最后回到开场问题：不仅要“改对”，还要“传播对、保持住、解释清”。')

# Save and render
if(Test-Path $FinalPptx){Remove-Item -LiteralPath $FinalPptx -Force}
$pres.SaveAs($FinalPptx,$ppSaveAsOpenXMLPresentation)
if(Test-Path $RenderDir){Remove-Item -LiteralPath $RenderDir -Recurse -Force}
New-Item -ItemType Directory -Force -Path $RenderDir | Out-Null
$pres.Export($RenderDir,'PNG',1280,720)

# Text overflow ledger (best-effort using TextFrame2 bound size)
$overflow=@()
foreach($slide in $pres.Slides){
 foreach($shape in $slide.Shapes){
  try{
   if($shape.HasTextFrame -eq $msoTrue -and $shape.TextFrame2.HasText -eq $msoTrue){
    $bh=$shape.TextFrame2.TextRange.BoundHeight
    $bw=$shape.TextFrame2.TextRange.BoundWidth
    if($bh -gt ($shape.Height+3) -or $bw -gt ($shape.Width+3)){
      $overflow += [pscustomobject]@{Slide=$slide.SlideIndex;Shape=$shape.Name;BoundW=[math]::Round($bw,1);BoxW=[math]::Round($shape.Width,1);BoundH=[math]::Round($bh,1);BoxH=[math]::Round($shape.Height,1)}
    }
   }
  }catch{}
 }
}
$overflow | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path (Split-Path $RenderDir) 'overflow-ledger.json') -Encoding UTF8

$pres.Close()
$ppt.Quit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($pres) | Out-Null
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ppt) | Out-Null
[GC]::Collect();[GC]::WaitForPendingFinalizers()

Write-Output "PPTX=$FinalPptx"
Write-Output "RENDER=$RenderDir"
Write-Output ("SLIDES=" + 21)
