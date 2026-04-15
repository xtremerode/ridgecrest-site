import re

raw = """[PX] AG1 - Kitchen Remodeling | kitchen design and remodeling [BROAD] | Imp:192 Clk:6 CTR:3.13% CPC:$24.57 Cost:$147.41 | IS:38.8% RankLost:17.7% Top:78% AbsTop:67% QS:N/A
[PX] AG7 - General Contractor and Neighborhood | home remodel contractor [BROAD] | Imp:120 Clk:5 CTR:4.17% CPC:$23.49 Cost:$117.43 | IS:40.5% RankLost:58.8% Top:88% AbsTop:57% QS:N/A
[PX] AG1 - Kitchen Remodeling | kitchen renovation near me [BROAD] | Imp:21 Clk:3 CTR:14.29% CPC:$25.77 Cost:$77.31 | IS:19.2% RankLost:17.3% Top:80% AbsTop:60% QS:N/A
[PX] AG7 - General Contractor and Neighborhood | general contractor Danville [BROAD] | Imp:29 Clk:2 CTR:6.90% CPC:$24.50 Cost:$49.01 | IS:44.4% RankLost:11.1% Top:94% AbsTop:94% QS:N/A
[PX] AG6 - Interior Design and Architecture | residential interior designers near me [BROAD] | Imp:2 Clk:2 CTR:100.00% CPC:$24.09 Cost:$48.17 | IS:50.0% RankLost:0.0% Top:100% AbsTop:100% QS:N/A
[PX] AG7 - General Contractor and Neighborhood | general contractor Walnut Creek [BROAD] | Imp:13 Clk:2 CTR:15.38% CPC:$23.80 Cost:$47.61 | IS:25.0% RankLost:17.5% Top:100% AbsTop:80% QS:N/A
[PX] AG7 - General Contractor and Neighborhood | custom home design build [BROAD] | Imp:15 Clk:2 CTR:13.33% CPC:$23.73 Cost:$47.46 | IS:75.0% RankLost:25.0% Top:67% AbsTop:67% QS:N/A
[PX] AG6 - Interior Design and Architecture | interior design firms near me [BROAD] | Imp:38 Clk:2 CTR:5.26% CPC:$23.44 Cost:$46.88 | IS:24.6% RankLost:10.8% Top:97% AbsTop:94% QS:N/A
[PX] AG5 - Home Additions and ADU | accessory dwelling unit contractor [BROAD] | Imp:89 Clk:1 CTR:1.12% CPC:$29.81 Cost:$29.81 | IS:28.8% RankLost:21.5% Top:93% AbsTop:55% QS:N/A
[PX] AG3 - Whole House and Home Remodel | home renovation Walnut Creek [BROAD] | Imp:9 Clk:1 CTR:11.11% CPC:$24.93 Cost:$24.93 | IS:13.9% RankLost:22.2% Top:40% AbsTop:40% QS:N/A
[PX] AG5 - Home Additions and ADU | home addition Walnut Creek [BROAD] | Imp:11 Clk:1 CTR:9.09% CPC:$24.63 Cost:$24.63 | IS:24.3% RankLost:10.8% Top:67% AbsTop:22% QS:N/A
[PX] AG1 - Kitchen Remodeling | complete kitchen remodel [BROAD] | Imp:11 Clk:1 CTR:9.09% CPC:$24.63 Cost:$24.63 | IS:26.1% RankLost:21.7% Top:83% AbsTop:33% QS:N/A
[PX] AG6 - Interior Design and Architecture | home interior designer near me [BROAD] | Imp:12 Clk:1 CTR:8.33% CPC:$23.93 Cost:$23.93 | IS:19.4% RankLost:19.4% Top:67% AbsTop:67% QS:N/A
[PX] AG7 - General Contractor and Neighborhood | general contractor kitchen remodel [BROAD] | Imp:13 Clk:1 CTR:7.69% CPC:$23.90 Cost:$23.90 | IS:50.0% RankLost:25.0% Top:100% AbsTop:75% QS:N/A
[PX] AG6 - Interior Design and Architecture | architect Walnut Creek [BROAD] | Imp:17 Clk:1 CTR:5.88% CPC:$23.74 Cost:$23.74 | IS:25.5% RankLost:10.6% Top:58% AbsTop:50% QS:N/A
[PX] AG3 - Whole House and Home Remodel | remodeling companies near me [BROAD] | Imp:20 Clk:1 CTR:5.00% CPC:$23.59 Cost:$23.59 | IS:19.1% RankLost:16.2% Top:77% AbsTop:31% QS:N/A
[PX] AG6 - Interior Design and Architecture | interior designer near me [BROAD] | Imp:22 Clk:1 CTR:4.55% CPC:$23.51 Cost:$23.51 | IS:36.4% RankLost:9.1% Top:88% AbsTop:88% QS:1
[PX] AG7 - General Contractor and Neighborhood | general contractor home remodel [BROAD] | Imp:37 Clk:1 CTR:2.70% CPC:$23.31 Cost:$23.31 | IS:41.3% RankLost:15.2% Top:94% AbsTop:83% QS:N/A
[PX] AG1 - Kitchen Remodeling | kitchen remodel Walnut Creek [BROAD] | Imp:11 Clk:1 CTR:9.09% CPC:$8.09 Cost:$8.09 | IS:16.2% RankLost:18.9% Top:83% AbsTop:50% QS:N/A
[PX] AG3 - Whole House and Home Remodel | home remodel contractor [BROAD] | Imp:46 Clk:0 CTR:0% CPC:$0 Cost:$0 | IS:32.1% RankLost:22.2% Top:88% AbsTop:65% QS:N/A
[PX] AG2 - Bathroom Remodeling | bathroom remodel contractor [BROAD] | Imp:45 Clk:0 CTR:0% CPC:$0 Cost:$0 | IS:32.9% RankLost:25.0% Top:75% AbsTop:42% QS:N/A
[PX] AG7 - General Contractor and Neighborhood | general contractor near me [BROAD] | Imp:61 Clk:0 CTR:0% CPC:$0 Cost:$0 | IS:30.6% RankLost:30.6% Top:91% AbsTop:73% QS:3
[PX] AG7 - General Contractor and Neighborhood | design build firm [BROAD] | Imp:41 Clk:0 CTR:0% CPC:$0 Cost:$0 | IS:61.3% RankLost:35.5% Top:100% AbsTop:84% QS:N/A
[PX] AG7 - General Contractor and Neighborhood | custom home builder near me [BROAD] | Imp:34 Clk:0 CTR:0% CPC:$0 Cost:$0 | IS:100.0% RankLost:0.0% Top:100% AbsTop:50% QS:N/A"""

# Parse
keywords = []
for line in raw.strip().split('\n'):
    parts = line.split(' | ')
    ag = parts[0].strip()
    kw_match = parts[1].strip()
    kw = kw_match.rsplit(' [', 1)[0]
    match = kw_match.rsplit('[', 1)[1].rstrip(']')
    
    metrics = {}
    for part in parts[2:]:
        for item in part.strip().split(' '):
            if ':' in item:
                k, v = item.split(':', 1)
                v = v.replace('%', '').replace('$', '').replace('NaN', '0')
                try:
                    metrics[k] = float(v) if v != 'N/A' else None
                except:
                    metrics[k] = v
    
    keywords.append({
        'ag': ag, 'kw': kw, 'match': match,
        'imp': int(metrics.get('Imp', 0)),
        'clk': int(metrics.get('Clk', 0)),
        'ctr': metrics.get('CTR', 0),
        'cpc': metrics.get('CPC', 0) or 0,
        'cost': metrics.get('Cost', 0) or 0,
        'is': metrics.get('IS', 0),
        'rank_lost': metrics.get('RankLost', 0),
        'top': metrics.get('Top', 0),
        'abs_top': metrics.get('AbsTop', 0),
        'qs': metrics.get('QS', None)
    })

# Analysis
total_cost = sum(k['cost'] for k in keywords)
total_imp = sum(k['imp'] for k in keywords)
total_clk = sum(k['clk'] for k in keywords)
with_clicks = [k for k in keywords if k['clk'] > 0]
without_clicks = [k for k in keywords if k['clk'] == 0 and k['imp'] > 0]

print("=" * 70)
print("SUMMARY")
print(f"Total keywords reporting: {len(keywords)}")
print(f"Keywords with clicks: {len(with_clicks)}")
print(f"Keywords with impressions but NO clicks: {len(without_clicks)}")
print(f"Total impressions: {total_imp}")
print(f"Total clicks: {total_clk}")
print(f"Total cost: ${total_cost:.2f}")
print(f"Overall CTR: {total_clk/total_imp*100:.2f}%")
print(f"Overall CPC: ${total_cost/total_clk:.2f}" if total_clk > 0 else "")

print("\n" + "=" * 70)
print("AD GROUP BREAKDOWN")
ag_data = {}
for k in keywords:
    ag = k['ag']
    if ag not in ag_data:
        ag_data[ag] = {'imp': 0, 'clk': 0, 'cost': 0, 'kw_count': 0}
    ag_data[ag]['imp'] += k['imp']
    ag_data[ag]['clk'] += k['clk']
    ag_data[ag]['cost'] += k['cost']
    ag_data[ag]['kw_count'] += 1

for ag, d in sorted(ag_data.items(), key=lambda x: -x[1]['cost']):
    ctr = d['clk']/d['imp']*100 if d['imp'] > 0 else 0
    cpc = d['cost']/d['clk'] if d['clk'] > 0 else 0
    print(f"\n  {ag}")
    print(f"    {d['kw_count']} keywords | {d['imp']} imp | {d['clk']} clk | CTR:{ctr:.1f}% | ${d['cost']:.2f} spent | CPC:${cpc:.2f}")

print("\n" + "=" * 70)
print("HIGH CTR + LOW IS = UNDERVALUED OPPORTUNITIES")
print("(Keywords clicking well but barely showing — raising bids here gets more of what works)")
for k in sorted(with_clicks, key=lambda x: -x['ctr']):
    if k['is'] and k['is'] < 50:
        print(f"  \"{k['kw']}\" — CTR:{k['ctr']:.1f}% but IS only {k['is']:.0f}% (RankLost:{k['rank_lost']:.0f}%)")

print("\n" + "=" * 70)
print("HIGH IMPRESSION, ZERO CLICK = POTENTIAL WASTERS OR AD COPY ISSUES")
for k in sorted(without_clicks, key=lambda x: -x['imp']):
    if k['imp'] >= 10:
        print(f"  \"{k['kw']}\" — {k['imp']} imp, 0 clicks, IS:{k['is']:.0f}%, RankLost:{k['rank_lost']:.0f}%")

print("\n" + "=" * 70)
print("KEYWORD OVERLAP: SAME QUERIES IN MULTIPLE AD GROUPS")
kw_to_ags = {}
for k in keywords:
    base = k['kw'].lower()
    if base not in kw_to_ags:
        kw_to_ags[base] = []
    kw_to_ags[base].append(k['ag'])
for kw, ags in kw_to_ags.items():
    if len(ags) > 1:
        print(f"  \"{kw}\" appears in: {', '.join(ags)}")

print("\n" + "=" * 70)
print("QUALITY SCORE ALERTS")
for k in keywords:
    if k['qs'] is not None and isinstance(k['qs'], (int, float)) and k['qs'] <= 3:
        print(f"  \"{k['kw']}\" — QS: {int(k['qs'])} (POOR)")

