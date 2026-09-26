import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
import pandas as pd
import datetime
import os
import time
import sys
import traceback

import warnings
warnings.filterwarnings("ignore")

def get_video_transcript(video_id):
    """Lấy nội dung chữ của video (tiếng Việt)."""
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        try:
            transcript = transcript_list.find_transcript(['vi'])
        except:
            transcript = transcript_list.find_generated_transcript(['vi'])
            
        transcript_data = transcript.fetch()
        formatter = TextFormatter()
        text_formatted = formatter.format_transcript(transcript_data)
        text_formatted = text_formatted.replace('\n', ' ')
        return text_formatted
    except Exception as e:
        return ""

def process_channel(channel_url, output_csv):
    print(f"\n--- Đang xử lý kênh: {channel_url} ---")
    
    ydl_opts_flat = {
        'extract_flat': True,
        'quiet': True,
    }
    
    video_ids = set()
    video_types = {}
    
    try:
        # Lấy từ tab videos
        with yt_dlp.YoutubeDL(ydl_opts_flat) as ydl:
            target_url_v = channel_url + '/videos' if not channel_url.endswith('/videos') else channel_url
            print(f"Đang trích xuất danh sách từ {target_url_v}...")
            info_v = ydl.extract_info(target_url_v, download=False)
            if 'entries' in info_v:
                for e in info_v['entries']:
                    if e.get('id'):
                        video_ids.add(e['id'])
                        video_types[e['id']] = 'Video'

        # Lấy từ tab shorts
        with yt_dlp.YoutubeDL(ydl_opts_flat) as ydl:
            target_url_s = channel_url.replace('/videos', '') + '/shorts'
            print(f"Đang trích xuất danh sách từ {target_url_s}...")
            info_s = ydl.extract_info(target_url_s, download=False)
            if 'entries' in info_s:
                for e in info_s['entries']:
                    if e.get('id'):
                        video_ids.add(e['id'])
                        video_types[e['id']] = 'Shorts'
                        
    except Exception as e:
        print(f"Lỗi khi trích xuất danh sách video: {e}")

    video_ids = list(video_ids)
    print(f"Tìm thấy tổng cộng {len(video_ids)} videos và shorts.")
    
    if len(video_ids) == 0:
        return

    ydl_opts_video = {
        'quiet': True,
        'skip_download': True,
        'ignoreerrors': True
    }
    
    data_rows = []
    
    with yt_dlp.YoutubeDL(ydl_opts_video) as ydl:
        for index, vid in enumerate(video_ids):
            print(f"Đang cào video {index+1}/{len(video_ids)}: {vid} ...")
            
            video_url = f"https://www.youtube.com/watch?v={vid}"
            
            try:
                info = ydl.extract_info(video_url, download=False)
            except Exception as e:
                print(f"Lỗi khi lấy metadata video {vid}: {e}")
                continue
                
            if not info:
                continue
                
            text = get_video_transcript(vid)
            
            video_type = video_types.get(vid, 'Video')
                
            date_str = info.get('upload_date', '')
            date_formatted = ''
            if date_str and len(date_str) == 8:
                date_formatted = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]} 00:00:00"
                
            duration_sec = info.get('duration', 0)
            if duration_sec:
                duration_formatted = str(datetime.timedelta(seconds=duration_sec))
            else:
                duration_formatted = '0:00'
                
            row = {
                'title': info.get('title', ''),
                'viewCount': info.get('view_count', 0),
                'likes': info.get('like_count', 0),
                'commentsCount': info.get('comment_count', 0),
                'date': date_formatted,
                'duration': duration_formatted,
                'type': video_type,
                'url': video_url,
                'text': text,
                'numberOfSubscribers': info.get('channel_follower_count', ''),
                'channelTotalViews': '', 
                'channelTotalVideos': len(video_ids)
            }
            
            tags = info.get('tags', [])
            if tags:
                for i in range(min(10, len(tags))):
                    row[f'hashtags/{i}'] = tags[i]
                    
            data_rows.append(row)
            
            if (index + 1) % 20 == 0:
                df_temp = pd.DataFrame(data_rows)
                df_temp.to_csv(output_csv, index=False, encoding='utf-8')
                print(f"  [Đã lưu tạm {index+1} videos]")
                
    print(f"\nĐã cào xong {len(data_rows)} video. Đang lưu vào {output_csv}...")
    df = pd.DataFrame(data_rows)
    df.to_csv(output_csv, index=False, encoding='utf-8')
    print("Lưu thành công!")

if __name__ == "__main__":
    dataset_dir = "/Users/anhvu/Documents/Tài liệu học tập/HK6/DMA/Dataset"
    if not os.path.exists(dataset_dir):
        os.makedirs(dataset_dir)
        
    channels = [
        {"url": "https://www.youtube.com/@vinamilk", "file": "VINAMILK_YOUTUBE_ALLFIELDS.csv"},
        {"url": "https://www.youtube.com/@THtrueMILKvn", "file": "THTRUEMILK_YOUTUBE_ALLFIELDS.csv"},
        {"url": "https://www.youtube.com/@NutiFoodVietNam", "file": "NUTIFOOD_YOUTUBE_ALLFIELDS.csv"}
    ]
    
    idx = -1
    if len(sys.argv) > 1:
        idx = int(sys.argv[1])
        if 0 <= idx < len(channels):
            channels = [channels[idx]]
            
    for channel in channels:
        output_path = os.path.join(dataset_dir, channel['file'])
        process_channel(channel['url'], output_path)
