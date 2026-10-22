"""Портрет клиента в новой коляске (Qwen Image 2.1 edit в локальном ComfyUI): <image1> — рендер новой коляски
(art_tests/portrait_chair.py), <image2> — нынешний портрет (персонаж, поза, стиль).
python art_tests/portrait_reseat.py <ключ> [seeds…]   -> scratchpad/poses/local/reseat_<ключ>_s<seed>…png"""
import os, sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
SP = r"C:\Users\wario\AppData\Local\Temp\claude\D--wheels-and-bones\d845888a-7a45-42b9-a337-635687a142cf\scratchpad"
sys.path.insert(0, SP)
from comfy_client import upload, queue, wait, download

JOBS = {   # ключ: (рендер коляски, портрет, описание коляски, руки)
    "sorceress": ("portrait_chair_m3/portrait_chair_m3_00_white.png", "client_sorceress.png",
                  "a Permobil M3 Corpus mid-wheel-drive power wheelchair: black contoured seat and high backrest with a "
                  "headrest, black armrests, a joystick controller with a red knob on the armrest, six wheels (big drive "
                  "wheels with purple three-spoke hubs in the middle, small casters front and back), glossy purple body "
                  "panels, black footplates",
                  "Her right hand rests on the joystick."),
    "goblin": ("portrait_chair_edge4/portrait_chair_edge4_00_white.png", "client_goblin.png",
               "a Quantum Edge 4 power wheelchair with the seat raised high on a black scissor lift: black seat and "
               "backrest with a headrest, black armrests, a joystick controller on the right armrest, a low black power "
               "base with red accents, six small black wheels, a black footplate",
               "His hand rests on the joystick."),
}


def white(path, name):
    im = Image.open(path).convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    bg.alpha_composite(im)
    tmp = os.path.join(SP, "poses", "local", name)
    bg.convert("RGB").save(tmp)
    return tmp


def node(cls, **inputs):
    return dict(class_type=cls, inputs=inputs)


key = sys.argv[1]
seeds = [int(s) for s in sys.argv[2:]] or [11, 22, 33]
chair, portrait, desc, hands = JOBS[key]
i1 = upload(os.path.join(ROOT, "tools", "render_out", chair), f"wnb_reseat_chair_{key}.png")
i2 = upload(white(os.path.join(ROOT, "assets", portrait), f"in_portrait_{key}.png"), f"wnb_reseat_char_{key}.png")
prompt = ("Redraw the character from <image2> sitting in the wheelchair from <image1>. Keep the character EXACTLY as in "
          "<image2>: the same face, hair, clothes, colours, proportions, expression and sitting pose, and the same clean "
          "cartoon art style with soft cel shading and dark outlines. Replace only the wheelchair: it must be exactly "
          "the wheelchair from <image1> — the same model, design, viewing angle and every part — drawn in the same "
          "cartoon style as <image2>. It is " + desc + ". " + hands + " The character sits naturally on the seat, back "
          "against the backrest, feet on the footplate. Whole character and wheelchair fully visible, uncropped. "
          "Plain pure white background, no shadow, no text.")
ids = []
for seed in seeds:
    g = {"1": node("UNETLoader", unet_name="qwen2.1\\qwen_image_2.1_int8_convrot.safetensors", weight_dtype="default"),
         "2": node("QwenImage21Cache", model=["1", 0], device="auto", dtype="default"),
         "3": node("CLIPLoader", clip_name="Qwen text_encoder\\qwen3vl_8b_int8_convrot.safetensors", type="qwen_image",
                   device="default"),
         "4": node("VAELoader", vae_name="qwen_image_2.1_vae_bf16.safetensors"),
         "L0": node("LoadImage", image=i1), "L1": node("LoadImage", image=i2),
         "6": node("TextEncodeQwenImage21", clip=["3", 0], prompt=prompt, negative_prompt="", resolution=0,
                   vae=["4", 0], **{"images.image_1": ["L0", 0], "images.image_2": ["L1", 0]}),
         "7": node("KSampler", model=["2", 0], seed=seed, steps=25, cfg=1.0, sampler_name="euler", scheduler="simple",
                   denoise=1.0, positive=["6", 0], negative=["6", 1], latent_image=["6", 2]),
         "8": node("VAEDecode", samples=["7", 0], vae=["4", 0]),
         "9": node("SaveImage", images=["8", 0], filename_prefix=f"wnb/reseat/{key}_s{seed}")}
    ids.append((seed, queue(g)))
for seed, pid in ids:
    for p in download(wait(pid, timeout=1800), os.path.join(SP, "poses", "local"), f"reseat_{key}_s{seed}"):
        print(p)
