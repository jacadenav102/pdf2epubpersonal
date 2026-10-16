import glob
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.config.parser import ConfigParser
from modules.table_rescue import processor_list_with_rescue
pdf = glob.glob("*.pdf")[0]
cfg = ConfigParser({"page_range": "41,47,266,277", "disable_tqdm": True}).generate_config_dict()
conv = PdfConverter(artifact_dict=create_model_dict(), config=cfg,
                    processor_list=processor_list_with_rescue(PdfConverter.default_processors))
r = conv(pdf)
for c in ("GRÁFICA V.1", "GRÁFICA V.4"):
    i = r.markdown.find(c); print("-----", c); print(r.markdown[max(0, i-350):i+150])
for name, im in r.images.items():
    print(name, im.size); im.save(f"tmp_rovo_img_{name.split('_')[2]}.png")
