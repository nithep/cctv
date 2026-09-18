#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Smoke test: torch/cv2/ultralytics import + YOLO scan on /tmp/ecs_main.jpg"""
import sys, time

t0 = time.time()
import torch
t1 = time.time()
import cv2
t2 = time.time()
from ultralytics import YOLO
t3 = time.time()
print(f"torch {torch.__version__} ({t1-t0:.1f}s) cv2 {cv2.__version__} ({t2-t1:.1f}s) ultralytics import ({t3-t2:.1f}s)")

model = YOLO("yolov8n.pt")
t4 = time.time()
print(f"model load {t4-t3:.1f}s")

res = model.predict("/tmp/ecs_main.jpg", conf=0.5, verbose=False)
names = res[0].names
persons = [(names[int(b.cls)], round(float(b.conf), 2)) for b in res[0].boxes if names[int(b.cls)] == "person"]
print(f"inference {time.time()-t4:.1f}s persons={persons} all_classes={sorted(set(names[int(b.cls)] for b in res[0].boxes))}")
print("SMOKE_OK")
