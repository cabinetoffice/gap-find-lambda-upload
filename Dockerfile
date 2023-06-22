FROM public.ecr.aws/lambda/python:3.10

COPY upload_function/app.py ./
COPY upload_function/requirements.txt ./

RUN yum update -y
RUN python3.10 -m pip install -r requirements.txt -t .

CMD ["app.lambda_handler"]
