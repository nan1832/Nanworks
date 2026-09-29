$ErrorActionPreference = "Stop"

$Ssh = "C:\WINDOWS\System32\OpenSSH\ssh.exe"
$Key = Join-Path ([Environment]::GetFolderPath("UserProfile")) ".ssh\id_ed25519_bridge"
$Login = "ph_teacher3@10.68.162.201"
$RemoteScript = @'
cd /datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/VisEdit-main || exit 1
ROOT=/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2/server_results/no_edit_mmke_alt_eval_7models_20260612_161034
echo "PERSISTENT_SSH_RESTART time=$(date) host=$(hostname)" | tee -a "$ROOT/run_status.log"
MMKE_SPLIT=eval RUN_ROOT="$ROOT" bash scripts/launch_no_edit_mmke_alt_7models_g07.sh
'@

$Encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($RemoteScript))
$Inner = "ssh -o BatchMode=yes -o ConnectTimeout=5 g07 'echo $Encoded | base64 -d | bash'"
& $Ssh -i $Key -o StrictHostKeyChecking=no -o ConnectTimeout=10 $Login $Inner
