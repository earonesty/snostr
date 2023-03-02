# Social Network (SN) integration for Nostr

## Goals

 - support for major social networks
 - auto follow in nostr based on npubs in bios
 - cross-post nostr -> legacy social networks

## Design

 - selenium/webdriver for SN api support (no need to give away your pwd)
 - runs locally
 - install via pip for now

## Usage

Example usage line, type --help for more info.

`snostr --twitter="user:pass" --npriv="nsec..." `

Example output:

```
INFO:root:got 138 contacts from wss://relay.nostr.vision
INFO:root:got 141 contacts from wss://relay.damus.io
INFO:root:got 137 contacts from wss://nostr-pub.wellorder.net
INFO:root:26 new follows
INFO:root:publishing 167 contacts
```
