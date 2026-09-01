"""Catalogue des moteurs : ce que le studio sait faire, et ce qu'il faut
telecharger pour chacun.

Module a part, et sans aucune dependance : l'installeur le lit avant meme
qu'aiohttp soit installe. Recopier cette liste dans l'installeur aurait garanti
qu'elle finisse par diverger du serveur.

vram : gigaoctets necessaires sur la carte. C'est ce qui decide quels moteurs
sont proposables sur une machine donnee.
"""

# fichiers : (sous-dossier, nom local, depot HF ou None, chemin distant)
CATALOGUE = {
 "klein4b": dict(titre="FLUX.2 klein 4B", famille="flux2", type="image", duree="60 s", vram=8.0, multilingue=True,
   pour="polyvalent, tres bon suivi du prompt, seul modele fiable pour du texte lisible dans l'image",
   fichiers=[("diffusion_models","flux-2-klein-4b.safetensors","Comfy-Org/vae-text-encorder-for-flux-klein-4b","split_files/diffusion_models/flux-2-klein-4b.safetensors"),
             ("text_encoders","qwen_3_4b.safetensors","Comfy-Org/vae-text-encorder-for-flux-klein-4b","split_files/text_encoders/qwen_3_4b.safetensors"),
             ("vae","flux2-vae.safetensors","Comfy-Org/vae-text-encorder-for-flux-klein-4b","split_files/vae/flux2-vae.safetensors")]),
 "klein9b": dict(titre="FLUX.2 klein 9B", famille="flux2", type="image", duree="90 s", vram=6.0, multilingue=True,
   pour="comme klein 4B mais matieres et decors plus riches ; le texte y devient illisible",
   fichiers=[("diffusion_models","flux-2-klein-9b-Q4_K_S.gguf","unsloth/FLUX.2-klein-9B-GGUF","flux-2-klein-9b-Q4_K_S.gguf"),
             ("text_encoders","qwen_3_8b_fp8mixed.safetensors","Comfy-Org/vae-text-encorder-for-flux-klein-9b","split_files/text_encoders/qwen_3_8b_fp8mixed.safetensors"),
             ("vae","flux2-vae.safetensors","Comfy-Org/vae-text-encorder-for-flux-klein-4b","split_files/vae/flux2-vae.safetensors")]),
 "flux1":   dict(titre="FLUX.1 dev", famille="flux1", type="image", duree="95 s", traduire=True, vram=8.3,
   pour="photographie et cinema : lumiere, atmosphere, profondeur de champ",
   fichiers=[("diffusion_models","flux1-dev-Q5_K_S.gguf","city96/FLUX.1-dev-gguf","flux1-dev-Q5_K_S.gguf"),
             ("text_encoders","t5xxl_fp8_e4m3fn_scaled.safetensors","comfyanonymous/flux_text_encoders","t5xxl_fp8_e4m3fn_scaled.safetensors"),
             ("text_encoders","clip_l.safetensors","comfyanonymous/flux_text_encoders","clip_l.safetensors"),
             ("vae","flux1-ae.safetensors",None,None)]),
 "realvis": dict(titre="RealVisXL V5.0", type="image", duree="25 s", traduire=True, vram=7.0,
   pour="photorealisme direct : portraits, produits, scenes reelles",
   fichiers=[("checkpoints","RealVisXL_V5.0.safetensors","SG161222/RealVisXL_V5.0","RealVisXL_V5.0_fp16.safetensors")]),
 "pony":    dict(titre="Pony Diffusion V6 XL", type="image", duree="25 s",
   traduire=True, etiquettes=True, vram=7.0,
   pour="anime, manga, illustration, personnages stylises, fan-art",
   prefixe="score_9, score_8_up, score_7_up, ",
   fichiers=[("checkpoints","ponyDiffusionV6XL.safetensors","LyliaEngine/Pony_Diffusion_V6_XL","ponyDiffusionV6XL_v6StartWithThisOne.safetensors"),
             ("vae","sdxl_vae_fp16_fix.safetensors","madebyollin/sdxl-vae-fp16-fix","sdxl.vae.safetensors")]),
 "edition": dict(titre="FLUX.2 klein — edition", famille="flux2", type="edition", duree="20 s", vram=8.0, multilingue=True,
   pour="modifier une image existante d'apres une consigne",
   fichiers=[("diffusion_models","flux-2-klein-4b.safetensors","Comfy-Org/vae-text-encorder-for-flux-klein-4b","split_files/diffusion_models/flux-2-klein-4b.safetensors"),
             ("text_encoders","qwen_3_4b.safetensors","Comfy-Org/vae-text-encorder-for-flux-klein-4b","split_files/text_encoders/qwen_3_4b.safetensors"),
             ("vae","flux2-vae.safetensors","Comfy-Org/vae-text-encorder-for-flux-klein-4b","split_files/vae/flux2-vae.safetensors")]),
 "wan5b":   dict(titre="Wan 2.2 TI2V-5B", type="video", duree="6 min", vram=9.5, multilingue=True,
   pour="video a partir d'un texte seul",
   fichiers=[("diffusion_models","Wan2.2-TI2V-5B-Q5_K_M.gguf","QuantStack/Wan2.2-TI2V-5B-GGUF","Wan2.2-TI2V-5B-Q5_K_M.gguf"),
             ("text_encoders","umt5_xxl_fp8_e4m3fn_scaled.safetensors","Comfy-Org/Wan_2.2_ComfyUI_Repackaged","split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors"),
             ("vae","wan2.2_vae.safetensors","Comfy-Org/Wan_2.2_ComfyUI_Repackaged","split_files/vae/wan2.2_vae.safetensors")]),
 "wan14b":  dict(titre="Wan 2.2 I2V-A14B", type="video_image", duree="12 min", vram=9.0, multilingue=True,
   pour="animer une image existante",
   fichiers=[("diffusion_models","Wan2.2-I2V-A14B-HighNoise-Q4_K_S.gguf","QuantStack/Wan2.2-I2V-A14B-GGUF","HighNoise/Wan2.2-I2V-A14B-HighNoise-Q4_K_S.gguf"),
             ("diffusion_models","Wan2.2-I2V-A14B-LowNoise-Q4_K_S.gguf","QuantStack/Wan2.2-I2V-A14B-GGUF","LowNoise/Wan2.2-I2V-A14B-LowNoise-Q4_K_S.gguf"),
             ("loras","wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors","Comfy-Org/Wan_2.2_ComfyUI_Repackaged","split_files/loras/wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors"),
             ("loras","wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors","Comfy-Org/Wan_2.2_ComfyUI_Repackaged","split_files/loras/wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors"),
             ("text_encoders","umt5_xxl_fp8_e4m3fn_scaled.safetensors","Comfy-Org/Wan_2.2_ComfyUI_Repackaged","split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors"),
             ("vae","wan_2.1_vae.safetensors","Comfy-Org/Wan_2.2_ComfyUI_Repackaged","split_files/vae/wan_2.1_vae.safetensors")]),
 "audio":   dict(titre="ACE-Step 1.5 turbo", type="audio", duree="95 s", vram=9.4,
   pour="musique vite produite pour degrossir une idee ; 8 etapes, rendu grossier",
   checkpoint="acestep_v1.5_xl_turbo_bf16.safetensors",
   fichiers=[("diffusion_models","acestep_v1.5_xl_turbo_bf16.safetensors",None,None),
             ("text_encoders","qwen_0.6b_ace15.safetensors",None,None),
             ("text_encoders","qwen_4b_ace15.safetensors",None,None),
             ("vae","ace_1.5_vae.safetensors",None,None)]),
 "planche": dict(titre="Planche BD / manga", type="planche", duree="45 s",
   traduire=True, etiquettes=True, vram=7.2,
   pour="planche de bande dessinee ou de manga : plusieurs cases, gouttieres, bulles VIDES",
   prefixe=("score_9, score_8_up, score_7_up, m4ng4, manga, comic, multiple views, "
            "monochrome, greyscale, screentone, halftone, ink drawing, "
            "thick black panel borders, white gutters between panels, "),
   fichiers=[("checkpoints","ponyDiffusionV6XL.safetensors","LyliaEngine/Pony_Diffusion_V6_XL","ponyDiffusionV6XL_v6StartWithThisOne.safetensors"),
             ("vae","sdxl_vae_fp16_fix.safetensors","madebyollin/sdxl-vae-fp16-fix","sdxl.vae.safetensors"),
             ("loras","manga-panels-m4ng4.safetensors","Muapi/vixon-s-anime-manga-styles-manga-panels","vixon-s-anime-manga-styles-manga-panels.safetensors")]),
 "fluidifier": dict(titre="Fluidite video (FILM)", famille="film",
   type="fluidifier", duree="30 s", vram=1.5, multilingue=True,
   pour="intercaler des images dans une video : plus fluide a duree egale, ou "
        "ralenti propre",
   fichiers=[("frame_interpolation","film_net_fp16.safetensors",
              "Comfy-Org/frame_interpolation",
              "frame_interpolation/film_net_fp16.safetensors")]),
 # ── retouche localisee ────────────────────────────────────────────────
 # Un seul graphe les sert (g_retouche_zone) : la seule difference est le
 # cote du masque qu'on remplace. Deux entrees quand meme, parce que c'est le
 # catalogue que lit l'aiguilleur, et « retoucher une zone » ne lui dirait pas
 # laquelle. Les fichiers sont ceux de l'edition PLUS BiRefNet, qui fabrique
 # le masque : une machine qui n'a que l'un des deux ne peut pas servir ces
 # moteurs, et le studio doit l'apprendre avant de lui confier le travail.
 "retoucher_fond": dict(titre="Retouche du fond (klein + BiRefNet)", famille="flux2",
   type="retoucher_fond", duree="15 s", vram=8.0, multilingue=True,
   pour="changer le decor autour du sujet en gardant le sujet exactement tel quel",
 fichiers=[("diffusion_models","flux-2-klein-4b.safetensors","Comfy-Org/vae-text-encorder-for-flux-klein-4b","split_files/diffusion_models/flux-2-klein-4b.safetensors"),
           ("text_encoders","qwen_3_4b.safetensors","Comfy-Org/vae-text-encorder-for-flux-klein-4b","split_files/text_encoders/qwen_3_4b.safetensors"),
           ("vae","flux2-vae.safetensors","Comfy-Org/vae-text-encorder-for-flux-klein-4b","split_files/vae/flux2-vae.safetensors"),
           ("background_removal","birefnet.safetensors","Comfy-Org/BiRefNet","background_removal/birefnet.safetensors")]),
 "retoucher_sujet": dict(titre="Retouche du sujet (klein + BiRefNet)", famille="flux2",
   type="retoucher_sujet", duree="15 s", vram=8.0, multilingue=True,
   pour="effacer ou remplacer le sujet d'une image en gardant le decor exactement tel quel",
 fichiers=[("diffusion_models","flux-2-klein-4b.safetensors","Comfy-Org/vae-text-encorder-for-flux-klein-4b","split_files/diffusion_models/flux-2-klein-4b.safetensors"),
           ("text_encoders","qwen_3_4b.safetensors","Comfy-Org/vae-text-encorder-for-flux-klein-4b","split_files/text_encoders/qwen_3_4b.safetensors"),
           ("vae","flux2-vae.safetensors","Comfy-Org/vae-text-encorder-for-flux-klein-4b","split_files/vae/flux2-vae.safetensors"),
           ("background_removal","birefnet.safetensors","Comfy-Org/BiRefNet","background_removal/birefnet.safetensors")]),
 # SAM 3.1 vise une zone par son NOM, la ou BiRefNet ne connait que « le
 # sujet » et « le fond ». Mesure : IoU 0,905 sur « the sky » contre une
 # reference independante, 0,983 sur « the car » compare a BiRefNet, et le
 # masque coute 1,2 s — autant que BiRefNet.
 #
 # LICENCE : « SAM License » de Meta. L'usage commercial est autorise, mais
 # ce n'est PAS un modele libre — redistribution aux memes termes,
 # retro-ingenierie interdite, clauses ITAR, et Meta peut modifier les
 # termes unilateralement. Le studio est sous AGPL-3.0 : ce modele est un
 # telechargement optionnel de l'utilisateur, pas une dependance du logiciel.
 "retoucher_zone": dict(titre="Retouche d'une zone nommee (klein + SAM 3.1)",
   famille="flux2", type="retoucher_zone", duree="15 s", vram=8.0,
   traduire=True,
   pour="refaire une partie precise d'une image designee par son nom — le ciel, une voiture, un panneau — en laissant tout le reste intact",
 fichiers=[("diffusion_models","flux-2-klein-4b.safetensors","Comfy-Org/vae-text-encorder-for-flux-klein-4b","split_files/diffusion_models/flux-2-klein-4b.safetensors"),
           ("text_encoders","qwen_3_4b.safetensors","Comfy-Org/vae-text-encorder-for-flux-klein-4b","split_files/text_encoders/qwen_3_4b.safetensors"),
           ("vae","flux2-vae.safetensors","Comfy-Org/vae-text-encorder-for-flux-klein-4b","split_files/vae/flux2-vae.safetensors"),
           ("checkpoints","sam3.1_multiplex_fp16.safetensors","Comfy-Org/sam3.1","checkpoints/sam3.1_multiplex_fp16.safetensors")]),
 "detourer": dict(titre="Detourage (BiRefNet)", famille="birefnet",
   type="detourer", duree="5 s", vram=1.0, multilingue=True,
   pour="isoler le sujet d'une image et rendre le fond transparent",
   fichiers=[("background_removal","birefnet.safetensors","Comfy-Org/BiRefNet",
              "background_removal/birefnet.safetensors")]),
 "agrandir": dict(titre="Agrandissement 4x (UltraSharp)", famille="esrgan",
   type="agrandir", duree="20 s", vram=2.0, multilingue=True,
   pour="agrandir une image existante sans en changer le contenu : 4x, textures "
        "et details restaures",
   fichiers=[("upscale_models","4x-UltraSharp.pth","Kim2091/UltraSharp","4x-UltraSharp.pth")]),
 "objet3d": dict(titre="Hunyuan3D 2.0", type="objet3d", duree="3 min", vram=5.0,
   pour="modele 3D au format .glb a partir d'une image ; sans image fournie, une image est generee d'abord",
   fichiers=[("checkpoints","hunyuan3d-dit-v2_fp16.safetensors",
              "Comfy-Org/hunyuan3D_2.0_repackaged",
              "split_files/hunyuan3d-dit-v2_fp16.safetensors")]),
 "klein9bhd": dict(titre="FLUX.2 klein 9B pleine precision", famille="flux2", type="image",
   duree="70 s", vram=18.0, multilingue=True,
   pour="comme klein 9B, mais l'encodeur de texte est en pleine precision : "
        "le suivi du prompt et les details montent d'un cran. Exige une grosse carte.",
   fichiers=[("diffusion_models","flux-2-klein-9b-Q8_0.gguf","unsloth/FLUX.2-klein-9B-GGUF","flux-2-klein-9b-Q8_0.gguf"),
             ("text_encoders","qwen_3_8b.safetensors","Comfy-Org/vae-text-encorder-for-flux-klein-9b","split_files/text_encoders/qwen_3_8b.safetensors"),
             ("vae","flux2-vae.safetensors","Comfy-Org/vae-text-encorder-for-flux-klein-4b","split_files/vae/flux2-vae.safetensors")]),
 "flux1hd": dict(titre="FLUX.1 dev pleine precision", famille="flux1", type="image",
   duree="110 s", traduire=True, vram=26.0,
   pour="FLUX.1 dev sans quantification, avec l'encodeur T5 complet : la meilleure "
        "photographie possible ici. Exige une tres grosse carte.",
   fichiers=[("diffusion_models","flux1-dev.safetensors","Comfy-Org/flux1-dev","flux1-dev.safetensors"),
             ("text_encoders","t5xxl_fp16.safetensors","comfyanonymous/flux_text_encoders","t5xxl_fp16.safetensors"),
             ("text_encoders","clip_l.safetensors","comfyanonymous/flux_text_encoders","clip_l.safetensors"),
             ("vae","flux1-ae.safetensors",None,None)]),
 "audioplus": dict(titre="ACE-Step 1.5 SFT", type="audio", duree="8 min", vram=9.4,
   pour="musique soignee : 50 etapes au lieu de 8, nettement plus musical. A choisir des que la qualite compte",
   checkpoint="acestep_v1.5_xl_sft_bf16.safetensors",
   fichiers=[("diffusion_models","acestep_v1.5_xl_sft_bf16.safetensors",
              "Comfy-Org/ace_step_1.5_ComfyUI_files",
              "split_files/diffusion_models/acestep_v1.5_xl_sft_bf16.safetensors"),
             ("text_encoders","qwen_0.6b_ace15.safetensors",None,None),
             ("text_encoders","qwen_4b_ace15.safetensors",None,None),
             ("vae","ace_1.5_vae.safetensors",None,None)]),
}

# Taille de chaque fichier, en gigaoctets, relevee sur Hugging Face.
# Deux moteurs partagent souvent des fichiers (klein4b et edition, par
# exemple) : additionner leurs poids surestimerait le telechargement.
# On compte donc toujours l union des fichiers reellement manquants.
TAILLES = {
    # Mesurees sur disque, comme les autres. Sans elles, poids() annonçait
    # « ~16 Go » pour la retouche d'une zone nommee au lieu de 17,9 : on
    # promettait moins que ce qu'on allait telecharger. (Le chiffre a bouge
    # avec le catalogue ; c'est poids() qui fait foi, pas ce commentaire.)
    ('checkpoints', 'sam3.1_multiplex_fp16.safetensors'): 1.75,
    ('background_removal', 'birefnet.safetensors'): 0.44,
    ('upscale_models', '4x-UltraSharp.pth'): 0.07,
    ('checkpoints', 'RealVisXL_V5.0.safetensors'): 6.94,
    ('checkpoints', 'hunyuan3d-dit-v2_fp16.safetensors'): 4.93,
    ('checkpoints', 'ponyDiffusionV6XL.safetensors'): 6.94,
    ('diffusion_models', 'Wan2.2-I2V-A14B-HighNoise-Q4_K_S.gguf'): 8.75,
    ('diffusion_models', 'Wan2.2-I2V-A14B-LowNoise-Q4_K_S.gguf'): 8.75,
    ('diffusion_models', 'Wan2.2-TI2V-5B-Q5_K_M.gguf'): 3.81,
    ('diffusion_models', 'acestep_v1.5_xl_sft_bf16.safetensors'): 9.97,
    ('diffusion_models', 'flux-2-klein-4b.safetensors'): 7.75,
    ('diffusion_models', 'flux-2-klein-9b-Q4_K_S.gguf'): 5.83,
    ('diffusion_models', 'flux-2-klein-9b-Q8_0.gguf'): 9.98,
    ('diffusion_models', 'flux1-dev-Q5_K_S.gguf'): 8.29,
    ('diffusion_models', 'flux1-dev.safetensors'): 23.8,
    ('loras', 'manga-panels-m4ng4.safetensors'): 0.23,
    ('loras', 'wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors'): 1.23,
    ('loras', 'wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors'): 1.23,
    ('text_encoders', 'clip_l.safetensors'): 0.25,
    ('text_encoders', 'qwen_3_4b.safetensors'): 8.04,
    ('text_encoders', 'qwen_3_8b.safetensors'): 16.38,
    ('text_encoders', 'qwen_3_8b_fp8mixed.safetensors'): 8.66,
    ('text_encoders', 't5xxl_fp16.safetensors'): 9.79,
    ('text_encoders', 't5xxl_fp8_e4m3fn_scaled.safetensors'): 5.16,
    ('text_encoders', 'umt5_xxl_fp8_e4m3fn_scaled.safetensors'): 6.74,
    ('vae', 'flux2-vae.safetensors'): 0.34,
    ('vae', 'sdxl_vae_fp16_fix.safetensors'): 0.33,
    ('vae', 'wan2.2_vae.safetensors'): 1.41,
    ('vae', 'wan_2.1_vae.safetensors'): 0.25,
}

# Requis, telechargeables, et dont la taille n'a JAMAIS ete relevee. Sans cette
# liste, poids() les comptait pour zero en silence : « fluidifier » annonçait
# « ~0 Go a prendre » pour un fichier qu'il allait bel et bien telecharger. Un
# plancher presente comme un total est une promesse qu'on ne tient pas.
#
# Relever la taille et retirer l'entree est la vraie reparation. En attendant,
# elle est NOMMEE, et banc_catalogue.py refuse tout fichier requis qui ne serait
# ni ici ni dans TAILLES.
SANS_TAILLE = {
    ('frame_interpolation', 'film_net_fp16.safetensors'):
        "jamais relevee : personne n'a note le poids du modele d'interpolation",
}


def fichiers_requis(cles):
    """Les fichiers a telecharger pour ces moteurs, sans doublon."""
    return {(s, n) for c in cles for s, n, r, _ in CATALOGUE[c]["fichiers"] if r}


def poids(cles):
    """Gigaoctets a telecharger pour ces moteurs, sans compter deux fois
    les fichiers qu ils partagent."""
    return round(sum(TAILLES.get(f, 0.0) for f in fichiers_requis(cles)), 1)


def poids_incertain(cles):
    """Vrai quand le chiffre rendu par poids() est un PLANCHER, pas un total.

    A dire a l'utilisateur : « au moins X Go » ne se lit pas comme « X Go », et
    c'est la difference entre une estimation et une promesse.
    """
    return bool(fichiers_requis(cles) & set(SANS_TAILLE))


POIDS = {c: poids([c]) for c in CATALOGUE}
