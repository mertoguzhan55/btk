from app.config import Configs
from app.logger import Logger
from app.fastapi import FastAPIServer
from app.crud import CRUDOperations
from app.label_extractor_from_video import LabelExtractor
from app.json_handler import JsonHandler
from app.rag_pipeline import RagPipeline
from app.video_transcriper import VideoTranscript

def main(args, configs):

    logger = Logger(**configs["logger"])
    logger.debug("############ [NAME OF PROJECT] CONFIGURATIONS ############")
    logger.debug(configs)

    transcripter = VideoTranscript(logger=logger)
    label_extractor = LabelExtractor(**configs["LabelExtractor"],logger=logger)
    json_handler = JsonHandler(**configs["JsonHandler"], logger=logger)
    rag_pipeline = RagPipeline(**configs["RagPipeline"], logger=logger)

    crud = CRUDOperations(**configs["crud"], logger=logger)
    fastapi = FastAPIServer(**configs["fastapi"], crud=crud, transcripter = transcripter, label_extractor = label_extractor, json_handler=json_handler, rag_pipeline = rag_pipeline, logger=logger)
    fastapi.run()

    print("is running")



if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-e", "--environment", type=str)
    args = parser.parse_args()

    configs = Configs().load(config_name=args.environment)
    main(args, configs)