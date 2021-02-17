# 実行前に，Credentailを入れてください．以下ウェブサイトを参考にしてください
#https://cloud.google.com/speech-to-text/docs/quickstart-client-libraries?hl=ja
#

# coding=utf-8
import csv
import subprocess
import os
from google.cloud import storage
from google.cloud import speech



# libraryの更新，jsonの提示　イマイチちゃんと動いてません．
def initialize():
    # key = 'export GOOGLE_APPLICATION_CREDENTIALS="/Volumes/.json"'
    update1 = 'pip install --upgrade google-cloud-speech --ignore-installed'
    update2 = 'pip install --upgrade google-cloud-storage'
    # subprocess.call(key, shell=True)
    subprocess.call(update1, shell=True)
    subprocess.call(update2, shell=True)



# 文字起こし
def transcribe_gcs(gcs_uri, file_path, file_path2, nspeakers):
    """Asynchronously transcribes the audio file specified by the gcs_uri."""

    client = speech.SpeechClient()

    audio = speech.RecognitionAudio(uri=gcs_uri)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.FLAC,
        sample_rate_hertz=32000,
        language_code="ja-JP",
        enable_word_time_offsets=True,
        diarization_config = {
            "enable_speaker_diarization": True,
            "min_speaker_count" : nspeakers,
            "max_speaker_count" : nspeakers,
        }
    )

    operation = client.long_running_recognize(config=config, audio=audio)

    print("Waiting for operation to complete...")
    result = operation.result(timeout=90)

    # Each result is for a consecutive portion of the audio. Iterate through
    # them to get the transcripts for the entire audio file.
    print("...Done")
    with open(file_path, 'w', encoding='utf-8') as f1:
        with open(file_path2, 'w', encoding='utf-8') as f2:
            for result in result.results:
                alternative = result.alternatives[0]
                print("Transcript: {}".format(alternative.transcript), file=f2)
                print("Confidence: {}".format(alternative.confidence), file=f2)

                for word_info in alternative.words:
                    word = word_info.word
                    wordtrim = word[0:word.find('|')]
                    start_time = word_info.start_time
                    end_time = word_info.end_time
                    speaker_tag = word_info.speaker_tag
                    print(
                        "{},{},{},{}".format(start_time.total_seconds(),end_time.total_seconds(),speaker_tag, wordtrim), file=f1
                        # "start_time: {}, end_time: {}, speaker_tag: {}, Word: {}".format(start_time.total_seconds(),end_time.total_seconds(),speaker_tag, wordtrim), file=f1
                        )

#結果の整理
def tailor_result(file1, file2):
    with open(file1, encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        DataAr = [row for row in reader]

    result = []
    N = 0
    result.append(DataAr[0])
    for item in DataAr[1:]:
        if item[2] == result[N][2]:
            result[N][1] = item[1]  # endtime
            result[N][3] = result[N][3] + item[3]  # word
        else:
            result.append(item)
            N = N + 1

    with open(file2, 'w', encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerows(result)

#ファイルのGoogle Cloud Storage上へのアップロード
def upload_blob(bucket_name, source_file_name, destination_blob_name):
    """Uploads a file to the bucket."""
    # bucket_name = "your-bucket-name"
    # source_file_name = "local/path/to/file"
    # destination_blob_name = "storage-object-name"

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_filename(source_file_name, timeout=3600)

    print(
        "File {} uploaded to {}.".format(
            source_file_name, destination_blob_name
        )
    )

# flacファイルの生成
def create_flac(directory, filename, filename_extension):
    #####オリジナルファイルの拡張子指定はここ
    original_file = directory + filename_extension
    convereted_file = directory + filename + '.flac'
    cmd =  'ffmpeg -i "'+ original_file + '" -ac 1 -ar 32000 "' + convereted_file + '"'
    # Zoom録音に合わせています．
    subprocess.call(cmd, shell=True)


#maxqda readableのファイルに変更する
def maxqda_readable(filepath1, filepath2):
    def seconds(number):
        num = int(number)
        h = num // 3600
        m = (num - 3600 * h) // 60
        s = num - 3600 * h - 60 * m
        nanos = number - num
        time = str(h).zfill(2) + ":" + str(m).zfill(2) + ":" + str(s).zfill(2)  # + "."  + str(nanos)[2:]
        return time

    with open(filepath1,
              encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        DArta = [row for row in reader]

    for item in DArta:
        temp0 = seconds(float(item[0]))
        temp1 = seconds(float(item[1]))
        item[0] = temp0
        item[1] = temp1  # endtime

    with open(filepath2, 'w', encoding="utf-8-sig") as f:
        for item in DArta:
            if int(item[2]) != 0:
                f.write(item[0] + '\n')
                f.write('speaker' + item[2] + ':')
                f.write(item[3] + '\n')
                f.write(item[1] + '\n')


### 実行
initialize()
print("end initialize")

##ファイル入力
filename_extension = input('Enter file name with file extension:')
filename = str(os.path.splitext(filename_extension))
print(filename_extension)
print(filename)
directory = input('Enter file directory:')
print(directory)
bucket_name = input('enter bucket name in google cloud storage:')
print(bucket_name)
nspeakers = input('enter number of speakers in the recordings:')

### 変数設定　
# directory = '/Volumes/'
# bucket_name = "your_bucket_name"


#変数計算
uri = 'gs://'+ bucket_name + '/' + filename + '.flac'
file_path1 = directory + filename + 'word.csv' #生の読み出し単語スタンプ結果
file_path2 = directory + filename + '.txt' #生の読み出し結果文章txt
file_path3 = directory + filename + '_tailored.csv' #整理後の読み出し結果
file_path4 = directory + filename + '_maxqda.txt' #整理後のMaxqda向け結果
source_file_name = directory + filename + '.flac'
destination_blob_name = filename + '.flac'

### 実行コマンド郡
create_flac(directory, filename, filename_extension)
print("endcreateflac")
upload_blob(bucket_name, source_file_name, destination_blob_name)
print ("enduploadblob")
transcribe_gcs(uri, file_path1, file_path2, nspeakers)
print("endtranscribe")
tailor_result(file_path1, file_path3)
print("end tailoring")
maxqda_readable(file_path3, file_path4)
print("end making maxqda readable file")
