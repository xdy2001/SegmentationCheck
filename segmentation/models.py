from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

# Create your models here.
class Tripitaka(models.Model):
    no = models.CharField(max_length=8, primary_key=True, verbose_name = _('Tripitaka|no'))
    name = models.CharField(max_length=128, verbose_name = _('Tripitaka|name'))
    n_volumes = models.SmallIntegerField(default=0, verbose_name = _('Tripitaka|n_volumes'))
    start = models.SmallIntegerField(verbose_name = _('Tripitaka|start'))
    end = models.SmallIntegerField(verbose_name = _('Tripitaka|end'))

    def __unicode__(self):
         return self.name

    class Meta:
        verbose_name = _('tripitaka')
        verbose_name_plural = _('tripitakas')

class Volume(models.Model):
    class Meta:
        verbose_name = _('Segmentation|volume')
        verbose_name_plural = _('Segmentation|volumes')
    no = models.CharField(max_length=16, primary_key=True, verbose_name = _('Volume|no'))
    tripitaka = models.ForeignKey(Tripitaka, null=False, verbose_name = _('Volume|tripitaka'))
    name = models.CharField(max_length=128, verbose_name = _('Volume|name'))
    number = models.SmallIntegerField(verbose_name = _('Volume|number'))
    n_pages = models.SmallIntegerField(verbose_name = _('Volume|n_pages'))
    start = models.SmallIntegerField(verbose_name = _('Volume|start'))
    end = models.SmallIntegerField(verbose_name = _('Volume|end'))

    def __unicode__(self):
        return u'%s %s' % (self.tripitaka.name, self.name)



class Text(models.Model):
    display = models.CharField(max_length=16)
    semanteme = models.ForeignKey("self", blank=True, related_name="Text")
    is_base = models.BooleanField(default=False)

    def __unicode__(self):
        return self.display

class Sutra(models.Model):
    name = models.CharField(max_length=128)
    def __unicode__(self):
        return self.name

class SutraInfo(models.Model):
    tripitaka = models.ForeignKey(Tripitaka)
    name = models.CharField(max_length=128)
    sutra = models.ForeignKey(Sutra)
    discription = models.CharField(max_length=512)
    author = models.CharField(max_length=64)
    start = models.SmallIntegerField()
    end = models.SmallIntegerField()

    def __unicode__(self):
         return self.name

class OPage(models.Model):
    no = models.CharField(max_length=32, primary_key=True)
    tripitaka = models.ForeignKey(Tripitaka)
    volume = models.ForeignKey(Volume)
    sutra_info = models.ForeignKey(SutraInfo)
    discription = models.CharField(max_length=128)
    number = models.SmallIntegerField()
    image_path = models.CharField(max_length=512)
    image_upload = models.ImageField(upload_to = 'opage_images',max_length=512,null=True)
    width = models.SmallIntegerField()
    height = models.SmallIntegerField()
    is_done = models.BooleanField(default=False)

# Create your models here.
class Page(models.Model):
    id = models.CharField(max_length=32, primary_key=True)
    image = models.CharField(max_length=512)
    o_page = models.ForeignKey(OPage, blank=True, null=True)
    image_upload = models.ImageField(upload_to = 'page_images',max_length=512,null=True)
    text = models.TextField()
    width = models.SmallIntegerField(default=0)
    height = models.SmallIntegerField(default=0)
    left = models.SmallIntegerField(default=0)
    right = models.SmallIntegerField(default=0)
    is_correct = models.SmallIntegerField(default=0)
    erro_char_cnt = models.IntegerField(default=0)
#is_correct value
## 0 unchecked(initial value )
## 1 correct
## -1 erro
## -2 Character erro
## -3 line erro
## -4 page  erro

    def __unicode__(self):
        return self.id

    def short_text(self):
        s_text = u''
        start_pos = self.text.find(u';')
        pos = self.text.find(u'\n')
        if start_pos != -1:
            s_text = self.text[start_pos + 1:pos].strip()
        return s_text


class Character(models.Model):
    id = models.CharField(max_length=32, primary_key=True)
    page = models.ForeignKey(Page)
    text = models.ForeignKey(Text, blank=True, null=True)
    char = models.CharField(max_length=4, db_index=True)
    image = models.CharField(max_length=512)
    #image = models.ImageField(upload_to = 'character_images',max_length=512,null=True)
    left = models.SmallIntegerField()
    right = models.SmallIntegerField()
    top = models.SmallIntegerField()
    bottom = models.SmallIntegerField()
    line_no = models.SmallIntegerField()
    char_no = models.SmallIntegerField()
    is_correct = models.SmallIntegerField(default=0,db_index=True)
#is_correct value
## 0 unchecked(initial value )
## 1 correct
## 2 manual correct
## -1 erro
## -2 with/height erro
## -3 line erro
## -4 page  erro
    #verification_user = models.ForeignKey(User, blank=True, null=True, on_delete=models.SET_NULL)

    def __unicode__(self):
        return u'%s:%s' % (self.id, self.char)

class CharacterStatistics(models.Model):
    char = models.CharField(max_length=4,db_index=True,primary_key=True)
    total_cnt = models.IntegerField(default=0)
    uncheck_cnt = models.IntegerField(default=0)
    err_cnt = models.IntegerField(default=0)
    uncertainty_cnt = models.IntegerField(default=0)


    def __unicode__(self):
        return u'%s:%d' % (self.char,self.total_cnt )

