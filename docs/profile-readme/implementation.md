# Profile README — Implementation

`update_profile.py` runs daily. It computes age from the BIRTHDAY env var,
pulls repo, star, follower, contributed and commit counts from the GraphQL
API, sums lines of code per owned repo through the REST contributor stats
endpoint (SHA256 hashed cache in cache/loc_cache.json, invalidated by
pushed_at), then rewrites tspan values by id in dark_mode.svg and
light_mode.svg. Nothing is written unless every API call succeeded.
`ascii_portrait.py` is the one time avatar converter. clean_avatar.py is a border flood fill that strips the avatar's baked in checkerboard background before conversion; the chain is avatar.png to avatar_clean.png to portrait_fragment.svg. The workflow lives in
.github/workflows/update-profile.yml and commits only when values changed.
The PROFILE_TOKEN secret is a read only fine grained PAT.
