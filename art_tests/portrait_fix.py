"""Точечная правка готового портрета (Qwen Image 2.1 edit): лишняя вторая подножка и т.п. Портрет кладётся на белый
квадрат 1024 (по центру), после правки обратно в assets идёт ТОЛЬКО изменившийся участок внутри зоны (лицо/поза не
трогаются). python art_tests/portrait_fix.py <ключ> [seeds…]   -> scratchpad/poses/local/fix_<ключ>_s<seed>_9_0.png
python art_tests/portrait_fix.py <ключ>=<seed> […]                -> вставка в assets/<портрет>.png"""
import os, subprocess, sys
from PIL import Image, ImageChops, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
SP = r"C:\Users\wario\AppData\Local\Temp\claude\D--wheels-and-bones\d845888a-7a45-42b9-a337-635687a142cf\scratchpad"
LOCAL = os.path.join(SP, "poses", "local")
sys.path.insert(0, SP)

FIX = {   # ключ: (портрет, что поправить, зона вставки x0,y0,x1,y1 в долях портрета)
    "sorceress": ("client_sorceress.png",
                  "Remove the second, lower pair of footplates under the front of the wheelchair (the two flat plates "
                  "below and in front of the small front casters). Keep the one footplate her feet rest on, under the "
                  "hem of her robe. Where the removed plates were, show the front casters and the white background.",
                  (0.45, 0.68, 1.0, 1.0)),
    "badger": ("client_f5.png",
               "Remove the two angled footplates hanging low in front of the wheelchair at the bottom left. Her feet stay "
               "exactly where they are, resting on the front of the seat platform. Where the removed footplates were, "
               "show the white background.",
               (0.0, 0.62, 0.6, 1.0)),
    "lizard": ("client_whillc2.png",
               "Remove the big lower footplate with the grid pattern at the very bottom front, between the two front "
               "wheels. Keep the small footplate her feet rest on. Where the removed plate was, show the dark base of "
               "the wheelchair and the white background.",
               (0.25, 0.72, 0.95, 1.0)),
    "leshy": ("client_leshy.png",
              "Remove the second, thinner footplate sticking out under the big footplate at the front. Keep the one big "
              "footplate his feet rest on. Where the removed plate was, show the white background.",
              (0.45, 0.72, 1.0, 1.0)),
}


def square(portrait):
    """Портрет на белом квадрате 1024 и как вернуть кадр назад (рамка в квадрате)."""
    im = Image.open(os.path.join(ROOT, "assets", portrait)).convert("RGBA")
    w, h = im.size
    side = max(w, h)
    bg = Image.new("RGBA", (side, side), (255, 255, 255, 255))
    bg.alpha_composite(im, ((side - w) // 2, (side - h) // 2))
    k = 1024 / side
    box = tuple(round(v * k) for v in ((side - w) // 2, (side - h) // 2, (side - w) // 2 + w, (side - h) // 2 + h))
    return im, bg.convert("RGB").resize((1024, 1024), Image.LANCZOS), box


def node(cls, **inputs):
    return dict(class_type=cls, inputs=inputs)


def generate(key, seeds):
    from comfy_client import upload, queue, wait, download
    portrait, what, _ = FIX[key]
    _, sq, _ = square(portrait)
    tmp = os.path.join(LOCAL, f"fix_in_{key}.png")
    sq.save(tmp)
    i1 = upload(tmp, f"wnb_fix_{key}.png")
    prompt = ("Edit <image1>. " + what + " Keep everything else EXACTLY the same: the character, face, pose, hands, "
              "the rest of the wheelchair, colours, the clean cartoon art style, size and position in the frame. "
              "Plain pure white background, no shadow, no text.")
    ids = []
    for seed in seeds:
        g = {"1": node("UNETLoader", unet_name="qwen2.1\\qwen_image_2.1_int8_convrot.safetensors", weight_dtype="default"),
             "2": node("QwenImage21Cache", model=["1", 0], device="auto", dtype="default"),
             "3": node("CLIPLoader", clip_name="Qwen text_encoder\\qwen3vl_8b_int8_convrot.safetensors",
                       type="qwen_image", device="default"),
             "4": node("VAELoader", vae_name="qwen_image_2.1_vae_bf16.safetensors"),
             "L0": node("LoadImage", image=i1),
             "6": node("TextEncodeQwenImage21", clip=["3", 0], prompt=prompt, negative_prompt="", resolution=0,
                       vae=["4", 0], **{"images.image_1": ["L0", 0]}),
             "7": node("KSampler", model=["2", 0], seed=seed, steps=25, cfg=1.0, sampler_name="euler",
                       scheduler="simple", denoise=1.0, positive=["6", 0], negative=["6", 1], latent_image=["6", 2]),
             "8": node("VAEDecode", samples=["7", 0], vae=["4", 0]),
             "9": node("SaveImage", images=["8", 0], filename_prefix=f"wnb/fix/{key}_s{seed}")}
        ids.append((seed, queue(g)))
    for seed, pid in ids:
        for p in download(wait(pid, timeout=1800), LOCAL, f"fix_{key}_s{seed}"):
            print(p)


def install(key, seed):
    portrait, _, zone = FIX[key]
    cur, _, box = square(portrait)
    w, h = cur.size
    gen = os.path.join(LOCAL, f"fix_{key}_s{seed}_9_0.png")
    name = f"fix_{key}"
    subprocess.run([sys.executable, os.path.join(SP, "cut_new.py"), f"{name}={gen}"], check=True, cwd=SP,
                   stdout=subprocess.DEVNULL)
    cut = os.path.join(ROOT, "art_tests", "new_v1", "cut", name + ".png")
    rep = os.path.join(LOCAL, name + "_rep.png")
    subprocess.run([sys.executable, os.path.join(HERE, "alpha_repair.py"), gen, cut, rep], check=True,
                   stdout=subprocess.DEVNULL)
    new = Image.open(rep).convert("RGBA").crop(box).resize((w, h), Image.LANCZOS)
    on_white = lambda im: Image.alpha_composite(Image.new("RGBA", im.size, (255, 255, 255, 255)), im).convert("RGB")
    diff = ImageChops.difference(on_white(cur), on_white(new)).convert("L").point(lambda v: 255 if v > 40 else 0)
    z = Image.new("L", (w, h), 0)
    z.paste(255, tuple(round(f * s) for f, s in zip(zone, (w, h, w, h))))
    mask = ImageChops.multiply(diff.filter(ImageFilter.MaxFilter(9)), z).filter(ImageFilter.GaussianBlur(2))
    Image.composite(new, cur, mask).save(os.path.join(ROOT, "assets", portrait), optimize=True)
    print(portrait, (w, h))


args = sys.argv[1:]
if "=" in args[0]:
    for a in args:
        install(*a.split("="))
else:
    generate(args[0], [int(s) for s in args[1:]] or [11, 22, 33])
