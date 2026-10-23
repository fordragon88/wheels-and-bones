# -*- coding: utf-8 -*-
"""Вырезка фона через Qwen Image 2.1 (локальный ComfyUI): правка «Remove the background, and output a PNG image» — VAE
отдаёт настоящий RGBA. Qwen слегка перерисовывает картинку, поэтому из его ответа берётся только АЛЬФА, а цвет —
с исходника (если кадр совпал). python art_tests/qwen_cut.py in.png out.png [seed]"""
import os, sys
import numpy as np
from PIL import Image

SP = r"C:\Users\wario\AppData\Local\Temp\claude\D--wheels-and-bones\d845888a-7a45-42b9-a337-635687a142cf\scratchpad"
sys.path.insert(0, SP)
from comfy_client import upload, queue, wait, download

src, dst = sys.argv[1], sys.argv[2]
seed = int(sys.argv[3]) if len(sys.argv) > 3 else 1
im = Image.open(src).convert("RGB")
up = upload(src, "wnb_qcut_" + os.path.basename(src))


def node(cls, **inputs):
    return dict(class_type=cls, inputs=inputs)


g = {"1": node("UNETLoader", unet_name="qwen2.1\\qwen_image_2.1_int8_convrot.safetensors", weight_dtype="default"),
     "2": node("QwenImage21Cache", model=["1", 0], device="auto", dtype="default"),
     "3": node("CLIPLoader", clip_name="Qwen text_encoder\\qwen3vl_8b_int8_convrot.safetensors", type="qwen_image",
               device="default"),
     "4": node("VAELoader", vae_name="qwen_image_2.1_vae_bf16.safetensors"),
     "L0": node("LoadImage", image=up),
     "6": node("TextEncodeQwenImage21", clip=["3", 0], prompt="Remove the background, and output a PNG image",
               negative_prompt="", resolution=0, vae=["4", 0], **{"images.image_1": ["L0", 0]}),
     "7": node("KSampler", model=["2", 0], seed=seed, steps=25, cfg=1.0, sampler_name="euler", scheduler="simple",
               denoise=1.0, positive=["6", 0], negative=["6", 1], latent_image=["6", 2]),
     "8": node("VAEDecode", samples=["7", 0], vae=["4", 0]),
     "9": node("SaveImageAdvanced", images=["8", 0], filename_prefix="wnb/qcut/cut",
               **{"format": "png", "format.bit_depth": "8-bit", "format.input_color_space": "sRGB"})}
p = download(wait(queue(g), timeout=1800), os.path.join(SP, "qcut"), "qcut_" + os.path.splitext(os.path.basename(src))[0])[0]
q = Image.open(p)
print("Qwen:", q.mode, q.size)
q = q.convert("RGBA").resize(im.size, Image.LANCZOS)
qa = np.asarray(q).astype(int)
a = np.asarray(im).astype(int)
op = qa[..., 3] > 200
diff = np.abs(qa[..., :3] - a)[op].mean() if op.any() else 999
print(f"сдвиг цвета на непрозрачном: {diff:.1f} (0 — кадр тот же)")
out = np.dstack([a, qa[..., 3]]).astype(np.uint8)          # цвет — исходный, альфа — от Qwen
res = Image.fromarray(out, "RGBA")
res = res.crop(res.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox())
res.save(dst)
q.save(os.path.splitext(dst)[0] + "_qwenrgba.png")
print("ok", res.size)
