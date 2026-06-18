# Anatomy of an Account Takeover

*A field report on a real attack I survived — what happened, the hidden backdoor almost nobody checks, and the incident response that closed the gap.*

## TL;DR

In June 2026, my primary account was compromised and used to trigger unauthorized money-transfer activity. The incident involved hidden fraud alerts and a **password-proof backdoor** that would have survived me changing my password.

I caught it quickly, ran a full incident response, killed the persistence mechanisms, reported the fraud inside the recovery window, and resolved the financial exposure through the provider's security process. The attacker is now locked out.

This is the sanitized story and the lessons — because the techniques that hit me hit thousands of people quietly, and most never find the real backdoor.

## The attack

It started where most breaches actually start: **reused and leaked passwords.** A password I'd used in more than one place had turned up in a data breach. That single leaked credential was the key.

Once the account was compromised, three things turned a login into a serious incident:

1. **Hid the evidence.** They planted a mail filter that automatically deleted every incoming message from my money-transfer provider. So while the fraud alerts were firing, they were being silently trashed before I ever saw them.

2. **Planted a password-proof backdoor.** This is the part that matters most. They authorized a malicious **OAuth application** — a "connected app" — with permission to send mail as me and read my files. OAuth tokens and passkeys **survive a password change.** You can reset your password ten times and the backdoor still works, because it never used your password in the first place. This was their real foothold.

3. **Triggered unauthorized transfer activity.** Multiple unauthorized transfers went to an unfamiliar recipient account. I'm intentionally omitting the amount, recipient, bank, and case details here for privacy and incident hygiene.

The recovery path had to be audited too. A recovery email can become the skeleton key to everything else, so it was treated as part of the same incident response instead of an afterthought.

## The incident response

I discovered it the morning the transfer activity appeared. From there it was a race on two clocks: **lock the attacker out**, and **report the transactions before funds moved further.**

What I did, in order:

- **Killed the active sessions.** Changed the password and force-signed-out every session I didn't recognize.
- **Hunted the persistence.** This is the step most people skip. Changing your password is *not* enough. I went into the account's **connected apps / OAuth grants** and found the malicious app. **Revoked it.** Then I checked **passkeys and security keys** and found a rogue one that could log in *without* a password — removed it. That's what explained the repeated reset attempts that kept coming *after* I'd changed the password.
- **Removed the evidence-hiding filter** so alerts could reach me again.
- **Secured the recovery email** the same way — new password, two-factor on, deep-checked for filters, forwarding, and backdoors of its own.
- **Reported the fraud fast.** Froze the card, filed the dispute with the transfer provider, and reported the unauthorized activity through the right fraud channels while the recovery window was still open.
- **Hardened everything.** Enrolled the primary email in the **strongest available account protection**, turned on app-based two-factor across the board, and started moving every account onto a password manager with a unique password.
- **Checked the devices.** Ran a full malware scan and a forensic look at the laptop and phone — both came back clean. The compromise came through leaked credentials, not malware on my machine.

## Timeline (generalized)

| When | Event |
|---|---|
| Months before | A reused password leaks in a third-party breach |
| Days before | Suspicious foreign logins begin; a security alert fires |
| The night before | Unauthorized transfer activity appears |
| The morning of | I discover the fraud, and the incident response begins |
| Within hours | Sessions killed, backdoor revoked, fraud reported, accounts hardened |
| Same day | The provider resolves the reported security issue |

## The hard lessons

These are the ones I'd tattoo on my arm now.

1. **Reused passwords are the root cause, not bad luck.** One leaked password unlocks every account that shares it. A password manager with a unique password per site isn't optional — it's the single highest-leverage thing you can do.

2. **A password change does NOT remove a backdoor.** OAuth "connected apps" and passkeys log in *without* your password and *survive* a reset. After any compromise, you have to manually audit and revoke connected apps, passkeys, and active sessions. Almost nobody checks this. It was the attacker's real foothold.

3. **Two-factor is necessary, not sufficient.** It blocks a plain password login — but a stolen session cookie or an OAuth grant walks right past it. Layers matter.

4. **Attackers hide the alarms.** A mail filter that quietly deletes alerts buys them days. If something feels off, check your filters and forwarding rules — not just your inbox.

5. **The recovery window is a race.** Unauthorized transfers are more likely to be resolved *if you report within hours*. Know how to freeze your card and file a dispute *before* you need to.

6. **Your recovery email is the real crown jewel.** It can reset everything else. If it has an old password and no two-factor, your "secure" main account is only as strong as that forgotten inbox.

## What I changed (the durable fix)

- A **password manager** with a unique, generated password on every account.
- **App-based two-factor / passkeys** instead of SMS wherever possible.
- The **strongest tier of account protection** on my primary email.
- **Backup codes saved offline**, recovery email and phone verified and secured.
- A standing habit of auditing **connected apps, passkeys, sessions, and filters** — not just passwords.

## Outcome

The attacker is locked out. The backdoors are gone. The financial exposure was resolved through the provider's security process. A follow-up login attempt after the cleanup was blocked by two-factor — proof the hardening held.

It was the worst day I've had with technology, and I came out of it knowing exactly how these attacks work from the inside.

## Why this is in my portfolio

I build AI systems — chatbots, RAG apps, agents — and reliability has always been my obsession. After this, **security is part of that same discipline.** Running a live incident response under pressure — identifying OAuth persistence, killing every foothold, and verifying the fix — is the same skill set I bring to making software trustworthy: assume things fail, find the hidden failure mode, and verify the fix instead of hoping.

If you want systems built by someone who has been on the wrong end of a real attack and knows what actually holds up — that's the kind of engineer I am.

## Score your own account security

The lessons above are also a checklist. The interactive tool on this page lets you score your own account security in 60 seconds and tells you the single most important gap to close first — built straight from what saved me.

*This account is fully sanitized: no real names, exact amounts, addresses, account numbers, or case references appear anywhere in this write-up. Educational only; not legal, financial, or professional security advice.*
