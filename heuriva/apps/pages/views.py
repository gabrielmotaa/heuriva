from django.contrib.auth.decorators import login_not_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render


@login_not_required
def index(request: HttpRequest):
    if request.user.is_authenticated:
        return redirect("analysis:project_list")

    return render(request, "pages/index.html")


@login_not_required
def robots(request: HttpRequest):
    return render(request, "robots.txt", content_type="text/plain")


@login_not_required
def heartbeat(request: HttpRequest):
    return HttpResponse("OK", content_type="text/plain")
