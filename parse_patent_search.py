''' Load a CSV file from PatSnap and create a CSV of independent claims '''

import re
import csv
import argparse

test_flag = True

if test_flag == False:
    # Initialize parser
    parser = argparse.ArgumentParser(description=
                                 'Split limitations in PatSnap CSV files and optionally remove dependent claims.')

    # Add required argument
    parser.add_argument("--i", type=str, required=True, help="Input Filename")

    # Add optional argument
    parser.add_argument("--r", type=bin, default=True, help="Remove dependent claims if True (Default True)")

    args = parser.parse_args()

    input_fn = args.i
    remove_dep_claims_flag = args.r
else:
    input_fn = '20200409084946808.XLS'
    remove_dep_claims_flag = True


def create_claim_list(raw_claims):
    ''' Convert a single string into individual claims '''
    #
    # Strip out the newline characters because they're often in the wrong place
    raw_claims  = raw_claims.strip('\n')
    #
    # just being lazy, using this to change raw_claims into a claim_list
    claim_list = raw_claims.splitlines()
    #
    # combine the parsed claim elements into single claims
    claim_list = combine_claims(claim_list)
    #
    # delete the cancelled claims
    claim_list = delete_cancelled_claims(claim_list)
    #
    # Make the claim list into a dictionary
    claim_dict = mk_claim_dict(claim_list)
    #
    # split out claims because not all claims incorporate \n
    claim_dict = split_claims(claim_dict)
    #
    # delete dependent claims
    if remove_dep_claims_flag:
        claim_dict = delete_dep_claims(claim_dict)
    #
    # split claims into limitations
    claim_dict = split_limitations(claim_dict)
    return claim_dict

def clean_raw_claims(raw_claims):
    ''' Remove non-claim elements from raw_claims '''
    # delete the " at the beginning and end of the claims
    raw_claims = raw_claims[1:-1]

    # search for the first numeral
    search_result = re.search(r'1\.', raw_claims)
    if search_result is None:
        search_result = re.search(r'1 ', raw_claims)
        if search_result is None:
            print("Unable to locate the first claim in" + raw_claims[0:39])
            return raw_claims
    raw_claims = raw_claims[search_result.start():]
    return raw_claims

def delete_cancelled_claims(claim_list):
    ''' Remove language around cancelled claims '''
    temp = []
    for i in range(len(claim_list)):
        res = re.search(r'cancell?ed', str.lower(claim_list[i]))
        if res is None:
            temp.append(claim_list[i])
    return temp

def combine_claims(claim_list):
    ''' Combine the claim elements to put each claim in its own element '''
    temp = []
    for i in range(len(claim_list)):
        res = re.search(r'^\d', claim_list[i])
        if res:
            temp.append(claim_list[i])
        else:
            temp[-1] += claim_list[i]
    return temp

def extract_claim_num(claim):
    ''' Extract the integer claim number from the claim text '''
    leader = re.search(r'\d{1,3} ?\d{0,2} ?\d{0,1} ?\. ', claim[0:5])
    if leader is not None:
        num_str = claim[0:(leader.end()-2)]
    else:        
        leader = re.search(r'\d{1,3} ?\d{0,2} ?\d{0,1} [A-Z]', claim[0:5])
        if leader is not None:
            num_str = claim[0:(leader.end()-2)]
        else:    
            leader = re.search(r'\d{1,3} ?\d{0,2} ?\d{0,1}[a-z]', 
                               str.lower(claim[0:5]))
            if leader is not None:
                num_str = claim[0:(leader.end()-1)]
            else:
                # there is no additional claim number
                return(-1)
    num_str = num_str.replace(' ', '')
    claim_num = int(num_str)
    return claim_num

def break_claim(claim, claim_num):
    ''' Take a single claim and break it into multiple claims '''
    ''' Pass the claim to be broken and the claim number that starts it '''
#    broken_claims = []
    num_search_str = ''
    # search for the next claim number beyond the current one
    claim_num_str = str(claim_num + 1)
    for i in range(len(claim_num_str)):
        num_search_str = num_search_str + claim_num_str[i] + ' ?'
    search_str = num_search_str + '\\. '
    leader = re.search(search_str, claim)
    if leader is None:
        search_str = num_search_str + ' [A-Z]'
        leader = re.search(r'\d{1,3} ?\d{0,2} ?\d{0,1} [A-Z]', claim)
    if leader is None:
        return [claim]
    broken_claims = [claim[0:(leader.start()-1)]]
    next_claim_chunk = claim[leader.start():]
    ret_claim_chunk = break_claim(next_claim_chunk, claim_num + 1)
    if isinstance(ret_claim_chunk, str):
        ret_claim_chunk = [ret_claim_chunk]
    broken_claims += ret_claim_chunk
    return broken_claims

def sort_dict(claim_dict):
    ''' Sort a claim dictionary based upon the indices '''
    temp = {}
    a = sorted(claim_dict)
    for index in a:
        temp.update({index: claim_dict[index]})
    return temp

def split_claims(claim_dict):
    ''' Separate combined claims '''
    # check to see if any claims are out of order. If so, then we need to combine claims to fix erroneous splitting
    while True:
        claim_nums = list(claim_dict.keys())
        prior_number = -1
        for number in claim_nums:
            if number < prior_number:
                # combine this claim with the prior claim
                claim_dict[prior_number] += claim_dict[number]
                del claim_dict[number]
                break
            else:
                prior_number = number
        if prior_number == claim_nums[-1]:
            break

    while True:
        claim_dict = sort_dict(claim_dict)
        claim_nums = list(claim_dict.keys())
        expected_claim_nums = [*range(claim_nums[0], len(claim_nums)+1)]

        if claim_nums != expected_claim_nums:
            # need to split claims
            index = 0
            for number in claim_nums:
                if number != expected_claim_nums[index]:
                    # need to breakup the prior claim
                    prior_claim_num = claim_nums[index-1]
                    claim_to_break = claim_dict[prior_claim_num]
                    broken_claims = break_claim(claim_to_break, 
                                                prior_claim_num)
                    if len(broken_claims[0]) == len(claim_to_break):
                        temp_num = prior_claim_num + 1
                        temp_claim = str(temp_num)
                        temp_claim += '. '
                        temp_claim += '*-*-*-*-*-*-*-*-*-*-*-* PLACEHOLDER FOR MISSING CLAIM *-*-*-*-*-*-*-*-*-*-*-*'
                        claim_dict.update({temp_num: temp_claim})
                        break
                    else:
                        del claim_dict[prior_claim_num]
                        for broken_index in range(len(broken_claims)):
                            new_claim = broken_claims[broken_index]
                            new_claim_num = extract_claim_num(new_claim)
                            claim_dict.update({new_claim_num: new_claim})
                        break
                index += 1
                    
        else:
            break

    # split the last claim if needed
    claim_dict = sort_dict(claim_dict)
    claim_nums = list(claim_dict.keys())
    last_claim_num = claim_nums[-1]
    last_claim = claim_dict[last_claim_num]
    broken_claims = break_claim(last_claim, last_claim_num)
    if broken_claims == last_claim:
        return claim_dict
    else:
        del claim_dict[last_claim_num]
        for broken_index in range(len(broken_claims)):
            new_claim = broken_claims[broken_index]
            new_claim_num = extract_claim_num(new_claim)
            claim_dict.update({new_claim_num: new_claim})
        claim_dict = sort_dict(claim_dict)

    return claim_dict

def delete_dep_claims(claim_dict):
    ''' Delete the dependent claims '''
    ind_claim_dict = {}
    for i in claim_dict:
        res1 = re.search(r'of claim', str.lower(claim_dict[i]))
        res2 = re.search(r'as claimed in ', str.lower(claim_dict[i]))
        res3 = re.search(r' claim \d', str.lower(claim_dict[i]))
        res4 = re.search(r' any of claims \d', str.lower(claim_dict[i]))
        res5 = re.search(r' the preceding claims', str.lower(claim_dict[i]))
        res6 = re.search(r'of any preceding claim', str.lower(claim_dict[i]))
        res7 = re.search(r'according to claim', str.lower(claim_dict[i]))
        res8 = re.search(r'according to one of the claims', str.lower(claim_dict[i]))
        if ((res1 is None) and (res2 is None) and (res3 is None) and (res4 is None)
                 and (res5 is None) and (res6 is None) and (res7 is None) and (res8 is None)):
            ind_claim_dict[i] = claim_dict[i]
    return ind_claim_dict

def split_limitations(claim_dict):
    ''' split claim limitations into separate lines '''
    for i in claim_dict:
        temp = claim_dict[i]
        temp = re.sub(':', r':\n', temp)
        temp = re.sub(';', r';\n', temp)
        temp = re.sub('comprising ', 'comprising\n', temp)
        while True:
            parens = re.search(r'\(\d{1,3}; ?\n ?\d{1,3}\)', temp)
            if parens:
                found_str = parens.group()
                alt_found_str = re.sub(r'\n', r'', found_str)
                temp = re.sub(found_str, alt_found_str, temp)
            else:
                break
        temp = re.split('\n', temp)
        claim_dict[i] = temp
    return claim_dict

def mk_claim_dict(claim_list):
    ''' Change the simple claim list into a claim dictionary '''
    claim_dict = {}
    for i in range(len(claim_list)):
        claim_num = extract_claim_num(claim_list[i])
        claim_dict.update({claim_num: claim_list[i]})
    return claim_dict


''' Main code '''
print(f'')
remove_dep_claims = True
output_fn = input_fn.replace('.CSV', '_ind.CSV')

with open(input_fn, mode='r') as in_file, open(output_fn, mode='w') as out_file:
    csv_reader = csv.DictReader(in_file)
    csv_writer = csv.writer(out_file)
    in_row_count = 0
    
    # cycle through each row in the input file
    for in_row in csv_reader:
        
        # for the first input row, read the column names
        if in_row_count == 0:
            print(f'Column names are {", ".join(in_row)}\n')
            in_row_count += 1
            
        # read in the elements of the current row
        # Publication Number, Application Number, Application Date, Title, Claims
        p_num = in_row["﻿Publication Number"]   # leading character NOT space
        a_num = in_row["Application Number"]
        a_date = in_row["Application Date"]
        title = in_row["Title"]
        raw_claims = in_row["Claims"]

        print()
        print(p_num)
        print()

        # clean up raw claims by eliminating 'CLAIMS:' and such
        raw_claims = clean_raw_claims(raw_claims)
#        print(raw_claims)
        
        claim_list = create_claim_list(raw_claims)
        
#        claim_ind = 0
        for temp in claim_list:            
            print(*claim_list[temp], sep='\n')
            claim_str = claim_list[temp]
            for lim_index in range(len(claim_str)):
                lim_str = claim_str[lim_index]
                if lim_index == 0:
                    csv_writer.writerow([p_num, a_num, a_date, title, lim_str])
                else:
                    csv_writer.writerow(['', '', '', lim_str])
#            claim_ind += 1
        in_row_count += 1
        
    print()
    print(f'Processed {in_row_count} patents.')
    
