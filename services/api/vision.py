"""Synthetic label-to-observation workflow; no private farm uploads or recipe mutation."""
from io import BytesIO
from dataclasses import asdict
from PIL import Image,ImageDraw,ImageFont
from pydantic import Field
from packages.contracts import Strict
from runtime.deepseek_gateway import DeepSeekGateway,RunBudget,DeepSeekResponseError
from services.api.views import ROOT

class LabelObservation(Strict):
    batch_id: str = Field(min_length=1,max_length=40)
    visible_condition: str = Field(min_length=1,max_length=150)
    uncertain: bool

def observe_fixture(run_id,budget=None,provider_user_id=None):
    label='FT-'+run_id[:6].upper()
    im=Image.new('RGB',(800,360),'#eef2d4');d=ImageDraw.Draw(im)
    font=ImageFont.load_default(size=64)
    d.text((40,50),'SYNTHETIC BATCH',fill='#143629',font=ImageFont.load_default(size=35))
    d.text((40,140),label,fill='#143629',font=font)
    out=BytesIO();im.save(out,format='PNG')
    with DeepSeekGateway.from_config(ROOT/'config/deepseek_runtime.json',budget=budget or RunBudget(max_requests=1,max_reserved_output_tokens=1024,max_wall_seconds=90),**({'user_id':provider_user_id} if provider_user_id else {})) as gateway:
        asset=gateway.normalize_image(out.getvalue(),asset_id='synthetic-label-'+run_id)
        completion=gateway.vision_json(prompt='Return JSON with batch_id (copy the visible FT- label exactly), visible_condition (a short description of the label only), uncertain (boolean). This is a synthetic label, not a plant health or yield assessment.',images=[asset],output_model=LabelObservation,max_tokens=1024)
    if completion.data.batch_id!=label:raise DeepSeekResponseError('Image content did not match the synthetic label')
    return dict(asset_id=asset.asset_id,source_sha256=asset.source_sha256,normalized_sha256=asset.normalized_sha256,origin='synthetic',observation=completion.data.model_dump(),review_status='label_verified_against_fixture',agronomic_measurement=False,audit=asdict(completion.audit))
