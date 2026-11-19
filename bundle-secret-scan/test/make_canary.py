#!/usr/bin/env python3
"""Print a random fake key of one kind, shaped to match its scan rule.

Generated at test time: a committed key-shaped literal trips push protection
and every secret scan that reads this repo.
"""

import secrets
import string
import sys

ALNUM = string.ascii_letters + string.digits
AWS_ID = string.ascii_uppercase + "234567"


def rand(length: int, alphabet: str = ALNUM) -> str:
    return "".join(secrets.choice(alphabet) for _ in range(length))


SHAPES = {
    "stripe-live": lambda: "sk_" + "live_" + rand(30),
    "stripe-restricted": lambda: "rk_" + "live_" + rand(30),
    "stripe-webhook": lambda: "whsec_" + rand(32),
    "resend": lambda: "re_" + rand(9) + "_" + rand(24),
    "openai-project": lambda: "sk-" + "proj-" + rand(48),
    "anthropic": lambda: "sk-" + "ant-api03-" + rand(80),
    "aws-access-key": lambda: "AKIA" + rand(16, AWS_ID),
}

if __name__ == "__main__":
    print(SHAPES[sys.argv[1]]())
