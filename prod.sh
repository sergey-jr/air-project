export OAUTHLIB_INSECURE_TRANSPORT=1 #delete if you have https
export GAPP_SECRET=b'\xc4` \xae\xd4\x89\x1a9\xd5\x05\xc9RK\xed\xb2G'
pip3 install -r requirements.txt
gunicorn app:app -p 8080