# -*- coding:utf-8 -*-
import json
import random
import redis
import datetime

from django.http import JsonResponse
from django.contrib.auth.decorators import user_passes_test, login_required, permission_required
from django.core.cache import cache
from django.db.models import F
from django.shortcuts import render, render_to_response, get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import generic

from segmentation.models import Character, CharacterStatistics
from libs.fetch_variants import fetcher
from utils.get_checked_character import get_checked_character
from django.contrib.auth.models import Group
from .models import UserCredit, CharMarkRecord, ClassificationTask, ClassificationCompareResult
from .tasks import classify_with_random_samples

class List(generic.ListView):
    template_name = 'characters/char_manage.html'
    def get_queryset(self):
        char_lst = CharacterStatistics.objects.select_related('charstock').all().order_by('-total_cnt','char')
        return  char_lst


class Index(generic.ListView):
    template_name = 'characters/char_list.html'
    def get_queryset(self):
        char_lst = CharacterStatistics.objects.select_related('charstock').all().order_by('-total_cnt','char')
        return  char_lst

def index(request):
    import pdb;pdb.set_trace()
    return render(request, 'characters/character_index.html')

def help(request):
    return render(request, 'characters/characters_help.html')

def recog_demo(request):
    return render(request, 'characters/characters_recog_demo.html')

def char_dashboard(request):
    return render(request, 'characters/char_dashboard.html')

def stacked_area_chart(request):
    return render(request, 'characters/stacked_area_chart.html')

def detail(request, character_id):
    char = get_object_or_404(Character, pk=character_id)
    #char = Character.objects.order_by('?').first()
    summary = json.dumps(char.page.summary)
    page = char.page
    t_char = page.locate_char(char)
    return render(request,'characters/character_detail.html',{'character': char, 'page': page,'t_char': t_char, 'summary': summary})

def browser(request, char):
    view_user = request.user
    user_group = request.user.username
    if view_user.is_authenticated():
        if view_user.is_superuser or view_user.date_joined.replace(tzinfo=None) < datetime.datetime(2017, 12, 1, 0, 54):
            return render(request, 'characters/browser/index.html', {'character': char, 'user_group': user_group})
        elif Group.objects.filter(user=view_user):
            user_group = Group.objects.filter(user=view_user)[0].name
            if user_group == 'verified' :
                return render(request,'characters/browser/index.html',{'character': char,'user_group': user_group})
            else:
                return render(request, 'characters/browser/readonly.html', {'character': char, 'user_group': user_group})
        else:
            return render(request, 'characters/browser/readonly.html', {'character': char, 'user_group': user_group})
    else:
        return render(request,'characters/browser/readonly.html',{'character': char,'user_group': user_group})


#@user_passes_test(lambda u:u.is_staff, login_url='/quiz')
@login_required(login_url='/account/login/')
def task(request):
    query = CharacterStatistics.objects.filter(total_cnt__lte=5,total_cnt__gt=0)
    total_cnt = query.count()
    select_cnt = query.filter(uncheck_cnt__gt=0).count()
    done_cnt = total_cnt - select_cnt

    today = timezone.now().strftime("%Y%m%d")
    checkin_date = request.session.get('checkin_date', 0)
    if checkin_date != today:
        #active_date=time.strptime(checkin_date,'%Y%m%d')
        check_char_number = request.session.get('check_char_number', 0)
        if check_char_number !=0:
            user_credit = UserCredit(user=request.user,
                                     active_date=checkin_date,
                                     credit=request.session['check_char_number'],
                                     username=request.user.username
                                     )
            user_credit.save()
        request.session['check_char_number'] = 0
        request.session['checkin_date'] = today
    check_char_number = request.session.get('check_char_number',0)
    char_lst = query.filter(uncheck_cnt__gt=0).order_by('-total_cnt')[:30]
    if char_lst:
        char = random.choice(char_lst).char
    else:
        char = u'无'
    #char = get_checked_character()
    #lq_variant = fetcher.fetch_variants(u'麤')
    lq_variant = ''
    return render(request,'characters/characters.html',{'char':char,
                                                        'check_char_number':check_char_number,
                                                        'done_cnt':done_cnt,
                                                        'total_cnt':total_cnt,
                                                        'variant_lst':lq_variant,
                                                        } )

@login_required(login_url='/account/login/')
def set_correct(request):
    if 'id' in request.POST:
        char_id = request.POST['id']
        is_correct = int(request.POST['is_correct'])
        char = request.POST['char']
        char.encode('utf-8')
        query_set = Character.objects.filter(id=char_id)
        query_set.update(is_correct=is_correct)
        Character.update_statistics(char)
        record = CharMarkRecord.create(request.user, char_id, is_correct, timezone.now())
        record.save()
        data = {'status': 'ok'}
    elif (('e_charArr[]' in request.POST) or ('c_charArr[]' in request.POST)): # uncheck -> check
        check_char_number = request.session.get('check_char_number', 0)
        request.session['check_char_number'] = check_char_number+1
        charArr = request.POST.getlist('e_charArr[]')
        char = request.POST['char']
        time = timezone.now()
        records = []
        if charArr:
            query_set = Character.objects.filter(id__in =charArr)
            query_set.update(is_correct=-1)
            Character.update_statistics(char)
            for char_id in charArr:
                record = CharMarkRecord.create(request.user, char_id, -1, time)
                records.append(record)
            CharMarkRecord.objects.bulk_create(records)

        charArr = request.POST.getlist('c_charArr[]')
        if charArr:
            query_set = Character.objects.filter(id__in =charArr)
            query_set.update(is_correct=1)
            Character.update_statistics(char)
            for char_id in charArr:
                record = CharMarkRecord.create(request.user, char_id, 1, time)
                records.append(record)
            CharMarkRecord.objects.bulk_create(records)

        data = {'status': 'ok'}
    elif ('cl_charArr[]' in request.POST):
        c_num = int(request.POST['c_num'])
        e_num = int(request.POST['e_num'])
        unset_num = e_num + c_num;
        char = request.POST['char']
        charArr = request.POST.getlist('cl_charArr[]')
        Character.objects.filter(id__in =charArr).update(is_correct=0)
        Character.update_statistics(char)
        time = timezone.now()
        records = []
        for char_id in charArr:
            record = CharMarkRecord.create(request.user, char_id, 0, time)
            records.append(record)
        if charArr:
            CharMarkRecord.objects.bulk_create(records)
        data = {'status': 'ok', 'clear': 'ok'}
    else:
        data = {'status': 'error'}
    return JsonResponse(data)


def tree_map(request):
    return render(request, 'characters/tree_map.html')

def get_marked_char_count(request):
    out_lst = cache.get('marked_char_count', None)
    if out_lst is None:
        sql = u'SELECT char, \
        count(CASE WHEN is_correct=1 THEN 1 END) as mark_correct_by_man, \
        count(CASE WHEN is_correct=-1 THEN 1 END) as mark_wrong_by_man, \
        count(CASE WHEN is_correct=0 and accuracy>=500 THEN 1 END) as mark_correct_by_pc, \
        count(CASE WHEN is_correct=0 and accuracy<500 THEN 1 END) as mark_wrong_by_pc \
    FROM segmentation_character GROUP BY char;'
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute(sql)
        results = cursor.fetchall()
        out_lst = []
        for r in results:
            d = {
                u'char': r[0],
                u'mark_correct_by_man': r[1],
                u'mark_wrong_by_man': r[2],
                u'mark_correct_by_pc': r[3],
                u'mark_wrong_by_pc': r[4],
            }
            out_lst.append(d)
        cache.set('marked_char_count', out_lst, timeout=86400)
    return JsonResponse({'status': 'ok', 'data': out_lst})

def classify(request):
    char = request.GET.get('char', None)
    if char is None:
        return JsonResponse({'status': 'error', 'msg': 'no char'})
    positive_sample_count = int(request.GET.get('positive_sample_count', 0))
    random_sample = int(request.GET.get('random_sample', 0))
    auto_apply = request.GET.get('auto_apply') == 'true'
    classify_with_random_samples.delay(char, positive_sample_count, auto_apply, random_sample)
    return JsonResponse({'status': 'ok'})

def accuracy_count(request):
    char = request.POST.get('char', None)
    if char is None:
        return JsonResponse({'status': 'error', 'msg': 'no char'})
    l_value = int(request.POST.get('min_value'))
    r_value = int(request.POST.get('max_value'))
    if ((r_value <= 0) or (l_value == r_value)):
        count = Character.objects.filter(char=char, is_correct=0, accuracy=l_value).count()
    elif (l_value > r_value):
        count = 0
    else:
        count = Character.objects.filter(char=char, is_correct=0, accuracy__gte=l_value, accuracy__lte=r_value).count()
    return JsonResponse({'count': count})

def marked_by_accuracy(request):
    char = request.POST.get('char', None)
    if char is None:
        return JsonResponse({'status': 'error', 'msg': 'no char'})
    l_value = int(request.POST.get('min_value'))
    r_value = int(request.POST.get('max_value'))
    if ((r_value <= 0) or (l_value == r_value)):
        _mark_based_scope(l_value, char)
    elif (l_value > r_value):
        count = 0
    else:
        if (r_value > 500):
            updateNum = Character.objects.filter(char=char, is_correct=0, accuracy__gte=l_value, accuracy__lte=r_value).update(is_correct=1)
        else:
            updateNum = Character.objects.filter(char=char, is_correct=0, accuracy__gte=l_value, accuracy__lte=r_value).update(is_correct=-1)
    Character.update_statistics(char)
    return JsonResponse({'status': 'ok'})

def _mark_based_scope(l_value, char):
    if l_value > 500:
        updateNum = Character.objects.filter(char=char, is_correct=0, accuracy=l_value).update(is_correct=1)
    else:
        updateNum = Character.objects.filter(char=char, is_correct=0, accuracy=l_value).update(is_correct=-1)
    Character.update_statistics(char)

def last_task_result(request):
    char = request.GET.get('char', None)
    last_task = ClassificationTask.objects.filter(char=char).last()
    data = []
    n = 0;
    for result in ClassificationCompareResult.objects.filter(task=last_task).select_related('character'):
        n+=1
        data.append({
                u'id': n,
                u'char': char,
                u'origin_accuracy': result.origin_accuracy*1.0/1000,
                u'new_accuracy': result.new_accuracy*1.0/1000,
                u'difference': result.difference*1.0/1000,
                u'url': result.character.image_url,
            })
        # data.append([n, char, result.origin_accuracy, result.new_accuracy,
        #      result.difference, result.character.image_url])
    return JsonResponse({'status': 'ok', 'data': data})

def more_task_result(request):
    char = request.GET.get('char', None)
    task_ids = ClassificationTask.objects.filter(char=char).values_list('id', flat=True)
    data = []
    n = 0;
    for result in ClassificationCompareResult.objects.filter(task_id__in=task_ids).order_by('-task_id').select_related('character'):
        n+=1
        data.append({
                u'id': n,
                u'char': char,
                u'origin_accuracy': result.origin_accuracy*1.0/1000,
                u'new_accuracy': result.new_accuracy*1.0/1000,
                u'difference': result.difference*1.0/1000,
                u'url': result.character.image_url,
            })
    return JsonResponse({'status': 'ok', 'data': data})
'''
def variant(request):
    lq_variant = fetcher.fetch_variants(u'麤')
    data = {'variant_lst':lq_variant}
    return  JsonResponse(data)
'''
