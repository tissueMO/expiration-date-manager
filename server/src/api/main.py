##############################################################################
#   Cloud Functions 互換のAPI群
##############################################################################

def health(request):
    return "OK"

def detect(request):
    print(request.data.decode())
    return "Detected OK."
