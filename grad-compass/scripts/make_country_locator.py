"""Build an offline Belgium locator from the app's bundled Natural Earth polygons."""
import hashlib
import json
import math
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]


def main():
    source=ROOT/'ui/data/countries.geo.json';raw=source.read_bytes();world=json.loads(raw)
    west,south,east,north=-6,45,12,56
    width,height=720,432;image=Image.new('RGB',(width,height),'#e3f1f4');draw=ImageDraw.Draw(image)
    merc=lambda lat:math.log(math.tan(math.pi/4+math.radians(lat)/2))
    def point(pair):return ((pair[0]-west)/(east-west)*width,(merc(north)-merc(max(-85,min(85,pair[1]))))/(merc(north)-merc(south))*height)
    for feature in world['features']:
        code=feature['properties']['ISO3166-1-Alpha-3'];geometry=feature['geometry'];polygons=geometry['coordinates'] if geometry['type']=='MultiPolygon' else [geometry['coordinates']]
        for rings in polygons:
            if not any(west-2<=p[0]<=east+2 and south-2<=p[1]<=north+2 for p in rings[0]):continue
            draw.polygon([point(p) for p in rings[0]],fill='#168aa0' if code=='BEL' else '#ffffff',outline='#94b5c0')
            for hole in rings[1:]:draw.polygon([point(p) for p in hole],fill='#e3f1f4')
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',20)
    draw.rounded_rectangle((18,18,258,56),radius=7,fill='#123c4e');draw.text((30,24),'Belgium · Western Europe',font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',16),fill='white')
    for label,coordinate in [('Belgium',(4.6,50.7)),('France',(1.6,47.4)),('Netherlands',(5.3,53)),('Germany',(9,50.9)),('United Kingdom',(-2.4,53.4))]:
        x,y=point(coordinate);draw.text((x,y),label,font=font,fill='#123c4e',anchor='mm',stroke_width=2,stroke_fill='#ffffff')
    target=ROOT/'web/assets/belgium-locator.png';image.save(target)
    manifest_path=ROOT/'web/assets/countries.json';manifest=json.loads(manifest_path.read_text());bel=manifest['BEL']
    bel['flag']={'path':'/assets/belgium-flag-small.svg','alt':'Belgium tricolour flag','credit':'Original vector by Grad Compass / Marry','license':'National symbol; original geometric rendering','sha256':hashlib.sha256((ROOT/'web/assets/belgium-flag-small.svg').read_bytes()).hexdigest()}
    bel['locator']={'path':'/assets/belgium-locator.png','alt':'Belgium highlighted in teal in Western Europe, with neighbouring countries for geographic context','caption':'Belgium in Western Europe. Geographic context only; no university or campus locations.','credit':'Grad Compass rendering · Natural Earth boundaries','source_url':'https://www.naturalearthdata.com/','license':'Public domain','license_url':'https://www.naturalearthdata.com/about/terms-of-use/','extent':[west,south,east,north],'projection':'Mercator, cropped to extent','transformation':'Country polygons projected, clipped and labelled; Belgium highlighted','source_file':'ui/data/countries.geo.json','source_sha256':hashlib.sha256(raw).hexdigest(),'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}
    manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')


if __name__=='__main__':main()
