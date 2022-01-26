from spot.prices.aws_price_retriever import AWSPriceRetriever
from spot.logs.aws_log_retriever import AWSLogRetriever
from spot.invocation.aws_function_invocator import AWSFunctionInvocator
from spot.invocation.aws_credentials_fetch import AWSCredentialsFetch
from spot.configs.aws_config_retriever import AWSConfigRetriever
from spot.mlModel.linear_regression import LinearRegressionModel
import json
import time as time
import os

class Spot:
    def __init__(self, config_file_path = "spot/config.json"):
        #Load configuration values from config.json
        self.config = None
        with open(config_file_path) as f:
            self.config = json.load(f)
            with open(self.config["workload_path"], 'w') as json_file:
                json.dump(self.config["workload"], json_file)

        #Set environment variables
        aws_creds = AWSCredentialsFetch()
        os.environ["AWS_ACCESS_KEY_ID"] = aws_creds.get_access_key_id()
        os.environ["AWS_SECRET_ACCESS_KEY"] = aws_creds.get_secret_access_key()

        #Instantiate SPOT system components
        self.price_retriever = AWSPriceRetriever(self.config["DB_URL"], self.config["DB_PORT"], self.config["region"])
        self.log_retriever = AWSLogRetriever(self.config["function_name"], self.config["DB_URL"], self.config["DB_PORT"])
        self.function_invocator = AWSFunctionInvocator(self.config["workload_path"], self.config["function_name"], self.config["mem_size"], self.config["region"])
        self.config_retriever = AWSConfigRetriever(self.config["function_name"], self.config["DB_URL"], self.config["DB_PORT"])
        self.ml_model = LinearRegressionModel(self.config["function_name"], self.config["vendor"], self.config["DB_URL"], self.config["DB_PORT"])#TODO: Parametrize ML model constructor with factory method


    def execute(self):
        print("Invoking function: ", self.config["function_name"])
        #invoke the indicated function
        self.invoke_function()
        
        print("Sleeping for 1 min to allow logs to propogate")
        #wait 1 min to allow logs to populate in aws
        time.sleep(60)

        print("Retrieving new logs and save in db")
        #collect log data
        self.collect_data()

        print("Training ML model")
        #train ML model accordingly
        self.train_model()

    def invoke_function(self):
        # fetch configs and most up to date prices
        self.config_retriever.get_latest_config()
        self.price_retriever.fetch_current_pricing()

        #invoke function
        self.function_invocator.invoke_all()

    def collect_data(self):
        #retrieve logs
        self.log_retriever.get_logs()

    def train_model(self):
        #train ml model
        self.ml_model.fetch_data()
        self.ml_model.train_model()