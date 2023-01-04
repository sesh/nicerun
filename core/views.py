from django.http import HttpResponse
from django.shortcuts import render

from activity_py import Activity


def home(request):
    if request.method == "POST":
        name = request.POST.get("name") or "Unnamed Run"
        f = request.FILES["file"]

        if f:
            if f.name.lower().endswith(".fit"):
                activity = Activity.load_fit(f)
            elif f.name.lower().endswith(".gpx"):
                activity = Activity.load_gpx(f)
            else:
                return HttpResponse("Unsupported File")

            activity.name = name

            return render(
                request,
                "run.html",
                {
                    "activity_json": activity.to_json(),
                },
            )

    return render(request, "home.html")


def run(request):
    pass
