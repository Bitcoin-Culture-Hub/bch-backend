# bch-backend
#  Bitcoin Culture Hub — Backend

This repo is the **backend for Bitcoin Culture Hub**, built with **FastAPI**.  
It powers our design and community features by handling all data and media connections.  
We use **MongoDB** for the database and **AWS S3** for image storage.

---

## Quick Start

```bash
git clone https://github.com/Bitcoin-Culture-Hub/bch-backend.git
pip install -r requirements.txt
uvicorn app.main:app --reload

