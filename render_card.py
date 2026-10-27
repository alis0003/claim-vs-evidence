"""Producer-only conversion of an already-inspected approved input. Requires Pillow."""
import argparse
import hashlib
import io
from pathlib import Path
from PIL import Image, ImageCms, ImageOps


def render(source, destination):
    with Image.open(source) as image:
        image.load()
        if image.info.get('icc_profile'):
            profile=ImageCms.ImageCmsProfile(io.BytesIO(image.info['icc_profile']))
            image=ImageCms.profileToProfile(image,profile,ImageCms.createProfile('sRGB'),outputMode='RGB')
        elif image.mode in ('RGBA','LA') or 'transparency' in image.info:
            rgba=image.convert('RGBA');background=Image.new('RGBA',rgba.size,'white')
            image=Image.alpha_composite(background,rgba).convert('RGB')
        else:image=image.convert('RGB')
        image=ImageOps.contain(image,(1080,1350),Image.Resampling.LANCZOS)
        canvas=Image.new('RGB',(1080,1350),'white')
        canvas.paste(image,((1080-image.width)//2,(1350-image.height)//2))
        output=Path(destination);output.parent.mkdir(parents=True,exist_ok=True)
        canvas.save(output,'JPEG',quality=93,optimize=True,progressive=False,
                    icc_profile=ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes())
        data=output.read_bytes()
        if len(data)>=8_000_000:raise ValueError('JPEG exceeds size limit')
        print('1080x1350 sRGB baseline JPEG',len(data),'bytes; SHA256',hashlib.sha256(data).hexdigest())
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path);parser.add_argument('destination',type=Path)
    args=parser.parse_args();render(args.source,args.destination)
