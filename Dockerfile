FROM public.ecr.aws/lambda/python:3.8

COPY upload_function/app.py ./
COPY upload_function/requirements.txt ./

RUN yum update -y
RUN python3.8 -m pip install -r requirements.txt -t .

CMD ["app.lambda_handler"]
