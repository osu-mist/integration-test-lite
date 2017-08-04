FROM python:2-onbuild

CMD [ "python", "./integration_test_lite.py", "configuration.json" ]

USER nobody:nogroup
