# NIQ Innovation Enablement - Challenge 1 (Object Counting)

The goal of this repo is demonstrate how to apply Hexagonal Architecture in a ML based system.

This application consists in a Flask API that receives an image and a threshold and returns the number of objects detected in the image.

The application is composed by 3 layers:

- **entrypoints**: This layer is responsible for exposing the API and receiving the requests. It is also responsible for validating the requests and returning the responses.

- **adapters**: This layer is responsible for the communication with the external services. It is responsible for translating the domain objects to the external services objects and vice-versa.

- **domain**: This layer is responsible for the business logic. It is responsible for orchestrating the calls to the external services and for applying the business rules.

The model used in this example has been taken from 
[IntelAI](https://github.com/IntelAI/models/blob/master/docs/object_detection/tensorflow_serving/Tutorial.md)


## Instructions to configure this project
```
# Download the rfcn model 
wget -O rfcn_resnet101_fp32_coco_pretrained_model.tar.gz \
      https://storage.openvinotoolkit.org/repositories/open_model_zoo/public/2022.1/rfcn-resnet101-coco-tf/rfcn_resnet101_coco_2018_01_28.tar.gz
tar -xzvf rfcn_resnet101_fp32_coco_pretrained_model.tar.gz -C tmp
rm rfcn_resnet101_fp32_coco_pretrained_model.tar.gz
chmod -R 777 tmp/rfcn_resnet101_coco_2018_01_28
mkdir -p tmp/model/rfcn/1
mv tmp/rfcn_resnet101_coco_2018_01_28/saved_model/saved_model.pb tmp/model/rfcn/1
rm -rf tmp/rfcn_resnet101_coco_2018_01_28
```

## Setup and run Tensorflow Serving

```
# For Mac M-series chips
docker compose up --build

# For unix systems
cores_per_socket=`lscpu | grep "Core(s) per socket" | cut -d':' -f2 | xargs`
num_sockets=`lscpu | grep "Socket(s)" | cut -d':' -f2 | xargs`
num_physical_cores=$((cores_per_socket * num_sockets))

docker rm -f tfserving
docker run \
    --name=tfserving \
    -p 8500:8500 \
    -p 8501:8501 \
    -v "$(pwd)\tmp\model:/models" \
    -e OMP_NUM_THREADS=$num_physical_cores \
    -e TENSORFLOW_INTER_OP_PARALLELISM=2 \
    -e TENSORFLOW_INTRA_OP_PARALLELISM=$num_physical_cores \
    intel/intel-optimized-tensorflow-serving:2.8.0 \
    --model_config_file=/models/model_config.config

# For Windows (Powershell)
$num_physical_cores=(Get-WmiObject Win32_Processor | Select-Object NumberOfCores).NumberOfCores
echo $num_physical_cores

docker rm -f tfserving
docker run `
    --name=tfserving `
    -p 8500:8500 `
    -p 8501:8501 `
    -v "$pwd\tmp\model:/models" `
    -e OMP_NUM_THREADS=$num_physical_cores `
    -e TENSORFLOW_INTER_OP_PARALLELISM=2 `
    -e TENSORFLOW_INTRA_OP_PARALLELISM=$num_physical_cores `
    intel/intel-optimized-tensorflow-serving:2.8.0 `
    --model_config_file=/models/model_config.config
```


## Run PostgreSQL and migrations

The production adapter stores cumulative object counts in PostgreSQL via SQLAlchemy ORM. Schema versioning is managed with Alembic.

```bash
docker compose up -d postgres
DATABASE_URL=postgresql+psycopg2://object_counter:object_counter@localhost:5432/object_counter alembic upgrade head
```


## Setup virtualenv

```bash
# Python >= 3.0
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# For MacOS/latest deployment
brew install python@3.9
virtualenv -p python3.9 venv
source venv/bin/activate
pip install -r requirements.txt
```

## Run the application

### Using fakes
```
python -m counter.entrypoints.webapp
```

### Using real services in docker containers

```
# Unix
ENV=prod python -m counter.entrypoints.webapp

# Powershell
$env:ENV = "prod"
python -m counter.entrypoints.webapp
```

## Call the service

```shell script
 curl -F "threshold=0.9" -F "file=@resources/images/boy.jpg" http://0.0.0.0:5001/object-count
 curl -F "threshold=0.9" -F "file=@resources/images/cat.jpg" http://0.0.0.0:5001/object-count
 curl -F "threshold=0.9" -F "file=@resources/images/food.jpg" http://0.0.0.0:5001/object-count 
```

## Run the tests

```
pytest
```