"""
Reads Atlas Live Events from Kafka for a time window
"""

from kafka import KafkaConsumer
import json
import time

from datetime import datetime

import logging 
import msgpack

from kafka.structs import TopicPartition, OffsetAndTimestamp

class EventConsumer():
    def __init__(self,startTS,windowInSeconds, topicName='default_atlas_probe_discolog'):
        self.topicName = topicName
        self.startTS = startTS

        self.consumer = KafkaConsumer(
                auto_offset_reset="earliest",
                enable_auto_commit=False,
                bootstrap_servers=['localhost:9092'],
                consumer_timeout_ms=1000,value_deserializer=lambda v: msgpack.unpackb(v, raw=False)
                )
        self.consumer.subscribe(topicName)

        self.windowSize = windowInSeconds * 1000    #milliseconds

        self.observers = []

    def attach(self,observer):
        if observer not in self.observers:
            self.observers.append(observer)

    def notifyObservers(self,data):
        for observer in self.observers:
            observer.eventDataProcessor(data)

    def start(self):
        timestampToSeek = self.startTS * 1000
        timestampToBreakAt = timestampToSeek + self.windowSize

        #print("Time Start: ",timestampToSeek,", Time End: ",timestampToBreakAt)

        self.consumer.poll(10000)
        topicPartitions = self.consumer.assignment()

        partitions_timestamps = dict( zip(topicPartitions, [timestampToSeek]*len(topicPartitions) ) )
        offsets = self.consumer.offsets_for_times(partitions_timestamps)

        for partition, toffset in offsets.items():
            self.consumer.seek(partition, toffset.offset)
        
        for message in self.consumer:
            messageTimestamp = message.timestamp

            if messageTimestamp > timestampToBreakAt:
                break

            msgAsDict = message.value

            self.notifyObservers(msgAsDict)


"""
#EXAMPLE

currentTS = int((datetime.utcnow() - datetime.utcfromtimestamp(0)).total_seconds())
eventReader = EventConsumer(currentTS,600*1000)
eventReader.attach(object) #Attach object that defines eventDataProcessor function
eventReader.start()"""
