# coding: utf-8
import os
from operator import itemgetter
from skimage import io
from skimage.filters import threshold_otsu
import numpy as np
import sys

sys.path.append('/home/dzj/SegmentationCheck')

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "SegmentationCheck.settings")
import django
django.setup()
from django.db import connection
from segmentation.models import Character

def binarisation(src_image):
    if len(src_image.shape) == 3:
        image = (src_image.sum(axis=2) / 3).astype('ubyte')
    else:
        image = src_image
    thresh = threshold_otsu(image)
    binary = (image < thresh).astype('ubyte')
    return binary

def main():
    with open('/home/dzj/abnormal_size.sql', 'w') as fsql:
        results = []
        count = Character.objects.count()
        iter_count = (count-1)/1000
        for i in range(iter_count):
            start = i*1000
            characters = Character.objects.all()[start: start+1000]
            for ch in characters:
                width = ch.right - ch.left
                height = ch.bottom - ch.top
                abnormal = True
                if height != 0:
                    ratio = width * 1.0 / height
                    if ratio >= 0.5 and ratio <= 2.0:
                        abnormal = False
                if abnormal:
                    sql = "UPDATE segmentation_character SET is_correct=-2 where id='%s';\n" % ch.id.encode('utf-8')
                    fsql.write(sql)
                    continue
                image = ch.image.encode('utf-8')
                filepath = '/data/share/dzj_characters/character_images/%s/%s' % (image[:-9], image)
                if not os.path.exists(filepath):
                    sql = "UPDATE segmentation_character SET is_correct=-5 where id='%s';\n" % ch.id.encode('utf-8')
                    fsql.write(sql)
                    continue
                is_white_black = False
                try:
                    src_image = io.imread(filepath)
                    binary = binarisation(src_image)
                    if np.sum(binary) < 20:
                        is_white_black = True
                    else:
                        binary = 1 - binary
                        if np.sum(binary) < 20:
                            is_white_black = True
                except:
                    is_white_black = True
                if is_white_black:
                    sql = "UPDATE segmentation_character SET is_correct=-6 where id='%s';\n" % ch.id.encode('utf-8')
                    fsql.write(sql)
                    continue

if __name__ == '__main__':
    main()

