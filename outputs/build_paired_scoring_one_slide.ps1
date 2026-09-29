$ErrorActionPreference='Stop'
$root=if($PSScriptRoot){Split-Path -Parent $PSScriptRoot}else{(Get-Location).Path}
$out=Join-Path $root 'outputs/paired_scoring_slide_20260922'
New-Item -ItemType Directory -Path $out -Force | Out-Null
$file=Join-Path $out 'BLIP2_L0_两种评分与编辑前后结果_单页.pptx'
if(Test-Path -LiteralPath $file){throw 'Output exists'}
function RGBColor($r,$g,$b){return [int]($r+256*$g+65536*$b)}
$navy=RGBColor 24 51 73
$blue=RGBColor 29 91 153
$green=RGBColor 16 112 95
$muted=RGBColor 92 108 124
$red=RGBColor 153 65 47
$white=RGBColor 255 255 255
$light=RGBColor 240 245 249
$app=New-Object -ComObject PowerPoint.Application
$pres=$app.Presentations.Add(0)
$pres.PageSetup.SlideWidth=1152
$pres.PageSetup.SlideHeight=648
$slide=$pres.Slides.Add(1,12)
$slide.FollowMasterBackground=0
$slide.Background.Fill.ForeColor.RGB=$white
function Txt($x,$y,$w,$h,$text,$size,$color,$bold=$false){
 $s=$slide.Shapes.AddTextbox(1,$x,$y,$w,$h)
 $t=$s.TextFrame
 $t.MarginLeft=0; $t.MarginRight=0; $t.MarginTop=0; $t.MarginBottom=0; $t.WordWrap=-1
 $t.TextRange.Text=$text
 $t.TextRange.Font.Name='Microsoft YaHei'; $t.TextRange.Font.NameFarEast='Microsoft YaHei'
 $t.TextRange.Font.Size=[single]$size; $t.TextRange.Font.Color.RGB=[int]$color
 $t.TextRange.Font.Bold=$(if($bold){-1}else{0})
 $t.TextRange.ParagraphFormat.SpaceAfter=0
 return $s
}
[void](Txt 36 24 1080 47 'BLIP2 L0编辑效果：两种评分，两种含义' 30 $navy $true)
[void](Txt 36 77 1080 26 'MMKE-entity官方955条配对评测　固定Epoch 24编辑器　2026-09-22完成　此次无参数更新' 15 $muted)
[void](Txt 36 116 523 30 'Teacher forcing：提供正确答案前缀' 21 $blue $true)
[void](Txt 36 153 520 68 "预测每个位置时，使用参考答案的正确前缀。`n准确率 = 预测正确的目标token数 / 目标token数。`n衡量条件预测能力，不能解释为整题答对比例。" 16 $navy)
[void](Txt 602 116 514 30 '自由生成：模型使用自己生成的前文' 21 $green $true)
[void](Txt 602 153 514 68 "只输入图片和问题，生成后与参考答案比较。`n词级F1 = 2PR / (P + R)，P、R衡量重叠词比例。`n衡量文字匹配程度，不直接代表语义正确率。" 16 $navy)
$rows=@(
 @('评测项目','TF编辑前 %','TF编辑后 %','变化 / pp','生成F1前 %','生成F1后 %','变化 / pp'),
 @('直接编辑目标','50.989','57.710','+6.721','4.283','13.896','+9.614'),
 @('问题改写','50.819','57.633','+6.814','6.630','13.275','+6.644'),
 @('图片变体','50.971','57.622','+6.652','4.239','13.746','+9.507'),
 @('图片关联问答','26.119','24.073','−2.046','1.124','0.966','−0.158'),
 @('文本关联问答','25.023','25.023','0.000','1.276','1.276','0.000'),
 @('1-hop问答','26.647','24.964','−1.683','1.853','1.801','−0.051'),
 @('无关图片问答¹','41.047','37.148','−3.900','1.184','0.941','−0.242'),
 @('无关文本问答¹','27.747','27.747','0.000','4.849','4.849','0.000')
)
$shape=$slide.Shapes.AddTable(9,7,36,235,1080,247)
$table=$shape.Table
$widths=@(216,144,144,126,162,162,126)
for($c=1;$c -le 7;$c++){$table.Columns.Item($c).Width=$widths[$c-1]}
for($r=1;$r -le 9;$r++){
 $table.Rows.Item($r).Height=27.45
 for($c=1;$c -le 7;$c++){
  $cell=$table.Cell($r,$c)
  $cell.Shape.Fill.ForeColor.RGB=$(if($r -eq 1){$navy}elseif($r%2 -eq 0){$light}else{$white})
  $tf=$cell.Shape.TextFrame
  $tf.MarginLeft=8; $tf.MarginRight=8; $tf.MarginTop=2; $tf.MarginBottom=2; $tf.VerticalAnchor=3
  $tr=$tf.TextRange; $tr.Text=[string]$rows[$r-1][$c-1]
  $tr.Font.Name='Microsoft YaHei'; $tr.Font.NameFarEast='Microsoft YaHei'; $tr.Font.Size=15
  $tr.Font.Bold=$(if($r -eq 1 -or $c -eq 4 -or $c -eq 7){-1}else{0})
  $tr.Font.Color.RGB=$(if($r -eq 1){$white}elseif(($c -eq 4 -or $c -eq 7) -and $tr.Text.StartsWith('+')){$green}elseif(($c -eq 4 -or $c -eq 7) -and $tr.Text.StartsWith('−')){$red}else{$navy})
  $tr.ParagraphFormat.Alignment=$(if($c -eq 1){1}else{2})
  foreach($side in 1..4){$cell.Borders.Item($side).ForeColor.RGB=RGBColor 222 230 238; $cell.Borders.Item($side).Weight=0.5}
 }
}
[void](Txt 36 499 1080 29 '结果含义：目标与改写表现提升，尚未带来关联知识和1-hop的同步改善' 21 $blue $true)
[void](Txt 36 538 1080 41 '完整作答仍受限：直接目标自由生成EM为0%（前后均为0），编辑后732/955条达到长度上限。' 17 $navy)
[void](Txt 36 580 1080 43 "¹ 此处按参考答案评分。Locality预测一致率另为文本100.000%、图片60.427%，常规五指标Average为66.679。`nF1使用归一化后的空格分词。1-hop生成F1差值的95%区间跨0；两列评分不可直接比高低。pp＝百分点。" 12.5 $muted)
$notes=@'
讲解顺序：左侧每个位置都看正确前缀，错误不沿生成链累积。右侧从头生成，使用自己的历史，错误可能累积。左侧模型分词器token位置准确率，右侧归一化词级重叠F1。
F1例子：参考red sports car，生成red car，P=1，R=2/3，F1=80%。P=重叠词数/生成词数，R=重叠词数/参考词数。忽略大小写、删除英文标点、去掉a/an/the，再按空格切词。不直接检查词序和语义。
每题先算评分，再汇总。955个唯一sample_id，无重复无缺失。图片和文本关联问答各1910道，其余各955道。95%区间以sample_id簇进行2000次配对bootstrap，seed42，未作多重比较校正。
直接目标TF提升6.720986个百分点，95%CI[6.497885,6.954636]。生成F1提升9.613811个百分点，CI[9.055780,10.215116]。1-hop生成F1变化−0.051315个百分点，CI[−0.239182,0.152115]。
自由生成：贪心，beam1，不采样，描述类最多512个新token，其他QA64个。直接目标达到长度上限：编辑前863/955，编辑后732/955。EM=0%不能直接等同于所有回答语义错误。
五指标：Rel57.709792，T-Gen57.633340，M-Gen57.622334，T-Loc100，M-Loc60.427408，Average66.678575。
冻结编辑器BLIP2-OPT-2.7B L0，epoch24/step7632/EMA6.124232。复用第一阶段checkpoint，不是第二阶段图谱方法训练成绩。官方955条与历史954条不可无说明覆盖。诊断结果不用于重新选层或调参。
来源：服务器/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main/phase2_p3/g1_paired_official955_20260921/paired_evidence_report.md及teacher/summary.json、free/summary.json、ALL_DONE。完成时间2026-09-22T08:45:46+08:00。2026-09-22 17:57服务器只读核验。
官方指标：phase2_p3/g1_reused_first_stage/official_eval955_repaired/layer_00/official_eval_full.done.json。
评分代码：phase2_p3/evaluate_g1_paired.py、additional_metrics.py。
'@
$slide.NotesPage.Shapes.Placeholders.Item(2).TextFrame.TextRange.Text=$notes
$pres.SaveAs($file,24)
$slide.Export((Join-Path $out 'preview.png'),'PNG',1920,1080)
$check=@()
foreach($s in $slide.Shapes){if($s.HasTextFrame -eq -1 -and $s.TextFrame.HasText -eq -1){$check+=@{text=$s.TextFrame.TextRange.Text;boxHeight=$s.Height;textHeight=$s.TextFrame.TextRange.BoundHeight;left=$s.Left;top=$s.Top;width=$s.Width}}}
$check | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 (Join-Path $out 'text_fit_check.json')
$pres.Close()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($pres) | Out-Null
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($app) | Out-Null
Write-Output $file
