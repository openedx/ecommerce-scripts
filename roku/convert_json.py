#!/usr/bin/env python
"""
Convert edX video content JSON file to Roku's Direct Publisher Feed (DPF) format.

See https://github.com/rokudev/feed-specifications/blob/master/direct-publisher-feed-specification.md for spec.
"""
import json
import math
from datetime import datetime
from urllib.parse import quote_plus


def convert_video(data, bitrate):
    return {
        'url': data['url'],
        'quality': 'HD',
        'videoType': 'MP4',
        'bitrate': bitrate,
    }


def convert_to_dpf(data):
    now = datetime.utcnow().isoformat()
    summary = data['summary']
    title = summary['name']
    captions = []
    thumbnail_url = 'http://via.placeholder.com/800x450?text=' + quote_plus(title)
    long_description = ''

    # FIXME This is only for the demo
    if summary['id'] == 'block-v1:UQx+Think101x+3T2016+type@video+block@598505eb528a4c1db41b827fa0b5050a':
        long_description = 'Lorem ipsum dolor sit amet, consectetur adipiscing elit. Duis in aliquet lectus. Cras porttitor, ipsum et pharetra auctor, augue erat efficitur nulla, sed aliquet sem mi nec urna. Aenean non urna orci. Curabitur interdum libero eu odio volutpat porttitor. Proin accumsan eros ut neque faucibus, sit amet imperdiet quam sollicitudin.'
        thumbnail_url = 'https://raw.githubusercontent.com/edx/ecommerce-scripts/roku/roku/a-taste.jpg'
        captions.append({
            'url': 'https://raw.githubusercontent.com/edx/ecommerce-scripts/roku/roku/a-taste.srt',
            'language': 'en',
            'captionType': 'SUBTITLE',
        })

    return {
        'id': summary['id'],
        'title': title,
        'content': {
            'dateAdded': now,
            'videos': [
                convert_video(summary['encoded_videos']['mobile_high'], 600),
                convert_video(summary['encoded_videos']['mobile_low'], 300),
            ],
            'duration': int(math.ceil(summary['duration'])),
            'captions': captions,
            # FIXME Subtitles require authentication
            # 'captions': [
            #     {
            #         'url': url,
            #         'language': language,
            #         'captionType': 'SUBTITLE',
            #     } for language, url in summary['transcripts'].items()
            # ],
            'language': summary['language'],
        },
        # FIXME Get actual thumbnails
        'thumbnail': thumbnail_url,
        'shortDescription': 'TBD',
        'longDescription': long_description,
        'releaseDate': now,
    }


if __name__ == '__main__':
    inputs = (
        ('The Science of Everyday Thinking', 'course-v1-UQx+Think101x+3T2016.json',),
    )

    videos = []
    playlists = []
    categories = []

    for name, input_file in inputs:
        with open(input_file) as data_file:
            parsed_input = json.load(data_file)

        converted = [convert_to_dpf(item) for item in parsed_input]
        videos.extend(converted)
        playlists.append({
            'name': name,
            'itemIds': [video['id'] for video in converted],
        })
        categories.append({
            'name': name,
            'playlistName': name,
            'order': 'manual',
        })

    feed = {
        'providerName': 'edX',
        'shortFormVideos': videos,
        'lastUpdated': datetime.utcnow().isoformat(),
        'playlists': playlists,
        'categories': categories,
    }
    print(json.dumps(feed, indent=2))
