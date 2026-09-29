import requests

urls = [
    "https://hf-mirror.com/spaces/Vision-CAIR/minigpt4/resolve/main/prerained_minigpt4_7b.pth",
    "https://storage.googleapis.com/sfr-vision-language-research/LAVIS/models/BLIP2/eva_vit_g.pth",
    "https://storage.googleapis.com/sfr-vision-language-research/LAVIS/models/BLIP2/blip2_pretrained_flant5xxl.pth",
    "https://hf-mirror.com/bert-base-uncased/resolve/main/config.json",
]

for url in urls:
    print(f"=== {url}")
    try:
        response = requests.head(url, allow_redirects=True, timeout=20)
        print(response.status_code, response.headers.get("content-length"), response.headers.get("content-type"))
    except Exception as exc:
        print(type(exc).__name__, exc)
