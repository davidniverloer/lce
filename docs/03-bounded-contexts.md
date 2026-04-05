# Bounded Contexts

## Overview
System is divided into 6 contexts:

1. IAM (Identity & Access)
2. Campaign Management
3. Market Intelligence
4. Content Intelligence
5. Content Repository
6. Notification & Audit

## Day 1 Scope
ONLY implement:

### Campaign Management
- Campaign entity
- Stores configuration

### Market Intelligence
- Topic entity
- Processes TopicGenerationRequested

### Minimal Audit (optional)
- store basic logs

## Ownership Rules
Each context:
- owns its data
- exposes events only
- does NOT access other DB tables

## Example Flow
Campaign → emits TopicGenerationRequested  
Market → consumes → creates Topic  
→ emits TopicQualified

## Future Contexts (ignore Day 1)
- Content Intelligence (agents)
- Repository (publishing)
- IAM (auth)