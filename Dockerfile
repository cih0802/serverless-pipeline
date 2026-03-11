# 1. AWS Lambda용 Python 3.12 베이스 이미지 사용
FROM public.ecr.aws/lambda/python:3.12

# 2. 작업 디렉토리 설정 (Lambda 전용 경로)
WORKDIR ${LAMBDA_TASK_ROOT}

# 3. 종속성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. 소스 코드 복사
COPY main.py .

# 5. 실행 핸들러 설정 (파일명.함수명)
# main.py 안에 있는 handler = Mangum(app)를 가리킵니다.
CMD [ "main.handler" ]