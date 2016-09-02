from django.shortcuts import render
from django.http import  JsonResponse
from django.views import generic
from catalogue.models import Tripitaka,Volume
from managerawdata.models import OPage
from os.path import splitext
from django.conf import settings
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import user_passes_test


class OpageIndex(generic.ListView):
    model = Tripitaka
    template_name = 'managerawdata/index.html'

    #@method_decorator(login_required)
    #@method_decorator(staff_member_required)
    @method_decorator(user_passes_test(lambda u:u.is_staff, login_url='/home/joinus'))
    def dispatch(self, *args, **kwargs):
        return super(OpageIndex, self).dispatch(*args, **kwargs)


def opage_upload(request):
    def handle_uploaded_file(f,page_id):
        ext = splitext(f.name)[1]
        file_name = 'opage_images/'+page_id+ext
        destination_file = settings.MEDIA_ROOT+file_name
        destination = open(destination_file, 'wb')
        for chunk in f.chunks():
            destination.write(chunk)
        destination.close()
        return file_name
    if request.method == 'POST':
        tripitaka_id = request.POST['tripitaka_id']
        volume_id = request.POST['volume_id']
        start_page = request.POST['start_page']
        page_type = int(request.POST['page_type'])

        page_no = int(start_page) + int(request.POST['file_id'])*page_type

        tripitaka = Tripitaka.objects.get(pk = tripitaka_id)
        volume = Volume.objects.get(pk = volume_id)
        page_id = '{0}-v{1:05}p{2:05}'.format(tripitaka.code,volume.number,page_no)

        image = handle_uploaded_file(request.FILES['file_data'],page_id)

        opage = OPage(
                id = page_id,
                tripitaka = tripitaka,
                volume = volume,
                page_type = page_type,
                page_no = page_no,
                image = image
            )
        opage.save()

        data = {'status': 'ok'}
        return JsonResponse(data)


    data = {'status': 'ok'}
    return JsonResponse(data)