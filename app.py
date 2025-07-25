from app.config import Configs
from app.logger import Logger

def main(args, configs):

    logger = Logger(**configs["logger"])
    logger.debug("############ [NAME OF PROJECT] CONFIGURATIONS ############")
    logger.debug(configs)

    print("is running")



if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-e", "--environment", type=str)
    args = parser.parse_args()

    configs = Configs().load(config_name=args.environment)
    main(args, configs)