#!/usr/bin/env python

# GloTool 1.0 - 2015-2018
# Split Glossika GMS MP3 files into individual sentences, and recombine.
# Joshua Miller - jtm.gg

import sys
import os
import argparse
import time
from glob import glob
from pydub import AudioSegment
from pydub.silence import detect_silence
from pydub.silence import detect_nonsilent

parser = argparse.ArgumentParser()
parser.add_argument('input_dirs', nargs='+', help='Single file or directory, MP3s')
parser.add_argument('-source', action='store', dest='source_name', default='source', help='Output source name, when splitting')
parser.add_argument('-target', action='store', dest='target_name', default='target', help='Output target name, when splitting')
parser.add_argument('-startnumber', action='store', dest='startnumber', type=int, default='1', help='What number to start output at, for splitting (501 would start naming files as 0501.mp3)')
parser.add_argument('-skipfirst', action='store', dest='skip_first', type=int, default='2', help='How many chunks to skip at the start of the file')
parser.add_argument('-skipend', action='store', dest='skip_end', type=int, default='1', help='How many chunks to skip at the end of the file')
parser.add_argument('-skipstartms', action='store', dest='skip_start_ms', type=int, default='0', help='How many millisecond to skip from the beginning of the file')
parser.add_argument('-detectsilencems', action='store', dest='detect_silence_ms', type=int, default='2000', help='How many milliseconds are considered a gap')
parser.add_argument('-gapaftersource', action='store', dest='gap_after_source', type=int, default='700', help='Duration of gap after source in milliseconds')

action = parser.add_mutually_exclusive_group()
action.add_argument('-s', action='store_true', default=False, dest='split', help='Used to split files')
action.add_argument('-j', action='store_true', default=False, dest='join', help='Used to join files')
parser.add_argument('-joinname', action='store', dest='join_output_name', help='Give a name to the files created when joined. For example - Custom_FR_EN would be used to make Custom_FR_EN-0001.mp3...')

inputtype = parser.add_mutually_exclusive_group()
inputtype.add_argument('-Bfiles', action='store_true', default=False, dest='B_files', help='used when B files are the input')
inputtype.add_argument('-Cfiles', action='store_true', default=False, dest='C_files', help='used when C files are the input')

arguments = parser.parse_args()

file_number = arguments.startnumber - 1

print('*GloTool*\n')

if arguments.split:
    if len(arguments.input_dirs) != 1:
        print('For splitting, input only one directory')
        sys.exit(0)
    if arguments.B_files:
        if (arguments.source_name is None) or (arguments.target_name is None):
            print('Please name the target and source language, so folders can be created with these names to store the output')
            sys.exit(0)
    if arguments.C_files:
        if (arguments.target_name is None):
            print('Please name the target language, so a folder can be created with this name to store the output')
            sys.exit(0)
    if (not arguments.B_files) and (not arguments.C_files):
        print('Please give -Bfiles or -Cfiles')
        sys.exit(0)

if arguments.join:
    if len(arguments.input_dirs) < 2:
        print('For joining, input two or more directories')
        sys.exit(0)
    if arguments.join_output_name is None:
        print('Give a name to the files created when joined. For example - Custom_FR_EN would be used to makea directory called Custom_FR_EN, containing Custom_FR_EN-0001.mp3, Custom_FR_EN-00051.mp3...')
        sys.exit(0)

def split_on_silence(audio_segment, min_silence_len=1000, silence_thresh=-16, keep_silence_start=100, keep_silence_end=100):

    print('Detecting silence...')
    not_silence_ranges = detect_nonsilent(audio_segment, min_silence_len, silence_thresh)

    chunks = []
    for start_i, end_i in not_silence_ranges:
        start_i = max(0, start_i - keep_silence_start)
        end_i += keep_silence_end

        chunks.append(audio_segment[start_i:end_i])
        
    return chunks

def gloSplit(fpath):
    print('Let\'s split...')
    t0 = time.time()

    print('** '+ os.path.basename(fpath) + ' **')
    if(fpath.lower().endswith('mp3')):
        sound = AudioSegment.from_mp3(fpath)
    elif (fpath.lower().endswith('wav')):
        sound = AudioSegment.from_wav(fpath)
    else:
        print('File not MP3 or WAV, ignoring...')
        # continue

    chunks = split_on_silence(sound[arguments.skip_start_ms:], 
        # must be silent for at least 2 seconds (default)
        min_silence_len = arguments.detect_silence_ms,
        # consider it silent if quieter than -48 dBFS
        silence_thresh = -48,
        keep_silence_start = 150,
        keep_silence_end = 300
    )


    if arguments.B_files:
        if not os.path.exists(arguments.source_name):
            os.makedirs(arguments.source_name)
    
    if not os.path.exists(arguments.target_name):
        os.makedirs(arguments.target_name)

    background_number = 0
    global file_number

    print('Writing files...')
    for i, chunk in enumerate(chunks):
        #ignore the intro part
        if i<arguments.skip_first:
            continue
        #ignore the outro
        if i >= (len(chunks) - arguments.skip_end):
            continue


        background_number+=1

        if arguments.B_files:
            #if number is odd save as source       
            if background_number%2 != 0:
                file_number+=1
                chunk.export(os.path.join(arguments.source_name, "{0:04d}.wav".format(file_number)), format="wav")
            else:
                chunk.export(os.path.join(arguments.target_name, "{0:04d}.wav".format(file_number)), format="wav")
        
        if arguments.C_files:
            file_number+=1
            chunk.export(os.path.join(arguments.target_name, "{0:04d}.wav".format(file_number)), format="wav")
    
    failed = False
    if (arguments.B_files and background_number == 100) or (arguments.C_files and background_number == 50):
        print("Wrote " + str(background_number) + " files - GOOD! *****************")
    else:
        print("Wrote " + str(background_number) + " files - BAD!  X-X-X-X-X-X-X-X-X")
        print("We detected too many sentences.")
        print("Try using -skipfirst X and -skipend X to fix.")
        failed = True

    t1 = time.time()
    seconds_taken = int(t1-t0)
    print("Took " + str(seconds_taken) + " seconds\n")
    
    if failed:
        print("Exiting")
        sys.exit(0)


def gloJoin(language_dirs):
    print('It\'s joining time...')

    after_source_silence = AudioSegment.silent(duration=arguments.gap_after_source)
    end_chime = AudioSegment.from_wav("chime.wav")

    combined = AudioSegment.empty()

    if not os.path.exists( os.path.join("output", arguments.join_output_name) ):
        os.makedirs( os.path.join("output", arguments.join_output_name) )
    
    for count in range(1,3001):
        source_audio = True
        for language_dir in language_dirs:
            single = AudioSegment.from_wav( os.path.join( language_dir, "{0:04d}.wav".format(count) ) )
            combined += single
            if source_audio:
                combined+= after_source_silence
                source_audio = False
            else:
                combined += AudioSegment.silent(duration=len(single))
        if (count)%50 == 0:
            combined += end_chime
            savename = arguments.join_output_name + " - " + "{0:04d}.mp3".format(count-49)
            combined.export( os.path.join("output", arguments.join_output_name, savename), format="mp3", tags={'artist': 'GloTool'})
            combined = AudioSegment.empty()
            print('Wrote ' + savename)
    print('Joining finished')



if(arguments.join):
    gloJoin(arguments.input_dirs)
if(arguments.split):
    if os.path.exists(arguments.input_dirs[0]):
        if (os.path.isdir(arguments.input_dirs[0])):
            for dname, dirs, files in os.walk(arguments.input_dirs[0]):
                for fname in files:
                    if(fname.lower().endswith('mp3')) or (fname.lower().endswith('wav')):
                        fpath = os.path.join(dname, fname)
                        if os.path.isfile(fpath):
                            gloSplit(fpath)

        elif os.path.isfile(arguments.input_dirs[0]):
            gloSplit(arguments.input_dirs[0])
