import subprocess
import json
import re
import time
import os
import sys
import multiprocessing
import time
import optparse 

direct = os.path.dirname(os.path.realpath(__file__))

default_timeout = -1
netkat_dist = direct + '/netkat_eq_dist.maude'
netkat_contra = direct + '/netkat_eq_contra.maude'
netkat_negation = direct + '/netkat_negation.maude'
netkat_total_order = direct + '/netkat_total_order.maude'
netkat_tests = direct + '/netkat_test.maude'
outfile = direct + '/output.txt'
maude_path = ''



def comm(program, cmd):
    proc = subprocess.Popen(['{} {} {}'.format(maude_path, program, cmd)],
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            shell=True,
                            cwd=direct)

    return proc.communicate()[0]     

def process_solutions(output):
    solutions = output.decode('utf-8')
    split = re.search('result (.*):', solutions).group(1)
    solutions = solutions.split('result {}:'.format(split), 1)[1]
    solutions = solutions.split('\nMaude>', 1)[0]
    solutions = solutions.rstrip().lstrip()
    solutions = solutions.replace('\n', '').replace('    ', ' ')
    return solutions

def export_file(filename, terms):
    f = open(filename, "w")
    f.write(terms)
    f.close()

def is_json(f):
  return len(f) > 5 and f[-5:] == ".json"

def is_exe(fpath):
    return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

def exists_in_path(program):
    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file
    return None

def equational(network, final_result):
    intermediate_result = {}
    intermediate_result[0] = [network['in']] 

    for i in range(1, network['unfold'] + 1):
        #policy, dist
        terms = 'red ((' + ''.join(intermediate_result[i-1]) + ') . (' + \
                network['policy']  + ')) .' 
        export_file(outfile, terms)
        output = comm(netkat_dist, outfile)
        output = process_solutions(output)
        summands = output.split('+')
        summands = ['(' + x + ')' for x in summands]
        
 
        #policy, contra
        terms = 'red ' + ' + '.join(summands) + '.'
        export_file(outfile, terms)
        output = comm(netkat_contra, outfile)
        output = process_solutions(output)
        

        #topology, dist
        terms = 'red ((' + output + ') . (' + \
                network['topology']  + ')) .'
        export_file(outfile, terms)
        output = comm(netkat_dist, outfile)
        output = process_solutions(output)
        summands = output.split('+')
        summands = ['(' + x + ')' for x in summands]


        #topology, contra
        terms = 'red ' + ' + '.join(summands)  + '.'
        export_file(outfile, terms)
        output = comm(netkat_contra, outfile)
        output = process_solutions(output)


        terms = 'red ' + output + ' . '
        export_file(outfile, terms)
        output = comm(netkat_tests, outfile)
        output = process_solutions(output)

        intermediate_result[i] = output
        

    for i in range(1, network['unfold'] + 2):
        terms = 'red ((' + ''.join(intermediate_result[i-1]) + ') . (' + \
                    network['out'] + ')) .'
        export_file(outfile, terms)
        output = comm(netkat_dist, outfile)
        output = process_solutions(output)
        summands = output.split('+')
        summands = ['(' + x + ')' for x in summands]


        terms = 'red ' + ' + '.join(summands)  + '.'
        export_file(outfile, terms)
        output = comm(netkat_contra, outfile)
        output = process_solutions(output)


        terms = 'red ' + output + ' . '
        export_file(outfile, terms)
        output = comm(netkat_dist, outfile)
        output = process_solutions(output)
        

        terms = 'red ' + output + ' . '
        export_file(outfile, terms)
        output = comm(netkat_tests, outfile)
        output = process_solutions(output)

        final_result[i-1] = output

def preprocess(network, processed_network):
    for term in ['in', 'policy', 'topology', 'out', 'fields', 'unfold']:
        processed_network[term] = network[term]

    #define the fields
    field_flag = False
    cat_flag = False
    field_terms = "\tprotecting NAT .\n\tsort Field .\n\tops "
    cat_terms = "\tops "
    order_terms = "\top _<_ : Field Field -> Bool [ctor] .\n\n"
    for j, field in enumerate(processed_network['fields']):
        field_terms += field['name'] + " "
        field_flag = True
        if field['type'] == "cat":
            cat_terms += ' ' + ' '.join(field['range'])
            cat_flag = True
        for k, innerfield in enumerate(processed_network['fields']):
            order_terms += "\teq {} < {} = {} .\n".format(field['name'],
                                                          innerfield['name'],
                                                          str(j<k).lower())
    if field_flag:
        field_terms += ": -> Field [ctor] .\n"
    else:
        field_terms = ''
    if cat_flag:
        cat_terms += " : -> Nat [ctor] .\n"
    else:
        cat_terms = ''

    for file in [netkat_dist, netkat_contra, netkat_negation, netkat_total_order, netkat_tests]:
        with open(file, "r") as in_file:
            buf = in_file.readlines()

        inside_field = False
        with open(file, "w") as out_file:
            for line in buf:
                if "fmod FIELD is" in line :
                    if file == netkat_total_order or file == netkat_tests:
                        line += field_terms + cat_terms + order_terms
                    else:
                        line += field_terms + cat_terms
                        
                    inside_field = True
                    out_file.write(line)
                if "endfm" in line:
                    inside_field = False
                if not inside_field:
                    out_file.write(line)

    #distribute negations over paranthesis
    for term in ['in', 'policy', 'topology', 'out']:
        if '~' in processed_network[term]:
            terms = 'red ' + processed_network[term] + ' . '
            export_file(outfile, terms)
            output = comm(netkat_negation, outfile)
            output = process_solutions(output)
            processed_network[term] = output

    #eliminate negations
    for term in ['in', 'policy', 'topology', 'out']:
        if '~' in processed_network[term]:
            atoms = processed_network[term].split('.')
            for i, e in enumerate(atoms):
                if '~' in e:
                    for field in processed_network['fields']:
                        if field['name'] in e:
                            value = e.split('=')[1].replace('(', '').replace(')','').rstrip().lstrip()
                            terms = []
                            if field['type'] == 'cat':
                                for j, r in enumerate(field['range']):
                                    if r != value:
                                        terms.append(field['name'] + " = " + r)
                                terms = "(" + ' + '.join(terms) + ")"
                            elif field['type'] == 'int':
                                value = int(value)
                                for j in range(field['range'][0], field['range'][1] + 1):
                                    if j != value:
                                        terms.append(field['name'] + " = " + str(j))
                                terms = "(" + ' + '.join(terms) + ")"
                            atoms[i] = terms
                            break
            processed_network[term] = ' . '.join(atoms)

    
    for term in ['in', 'policy', 'topology', 'out']:
        #bring the terms into disjunctive normal form
        terms = 'red ' + processed_network[term] + ' . '
        export_file(outfile, terms)
        output = comm(netkat_dist, outfile)
        output = process_solutions(output)

        #bring the fields into a fixed order
        terms = 'red ' + output + ' . '
        export_file(outfile, terms)
        output = comm(netkat_total_order, outfile)
        output = process_solutions(output)
        processed_network[term] = output

def report_result(result):
    counter = 0
    report = {}
    for key, value in result.items():
        if not value == 'zero':
            if '+' in value:
                value = value.split('+')
                for i, e in enumerate(value):
                    counter += 1
                    print('\nViolation: {}'.format(counter))
                    print('Path length: {}'.format(key))
                    print('Trace: {}'.format(e))
                    print('----\n')
                    report[counter] = e
                    
            else:
                counter += 1
                print('\nViolation: {}'.format(counter))
                print('Path length: {}'.format(key))
                print('Trace: {}'.format(value))
                print('----\n')
                report[counter] = value
    return report, counter

def label_atoms(report):
    label = {}
    counter = 0
    for i, e in report.items():
        atoms = e.split('.')
        for j, a in enumerate(atoms):
            a = a.lstrip().rstrip()
            if not a in label:
                label[a] = "p{}".format(counter)
                counter += 1
            atoms[j] = label[a]
        report[i] = '.'.join(atoms)

    return report

def extract_minimal_traces(report):
    labeled = label_atoms(report)

    not_minimals = []
    for i, e in labeled.items():
        if i not in not_minimals:
            atoms = e.split('.')
            pair_set = [('.'.join(atoms[0:i]), '.'.join(atoms[i:])) for i in range(1, len(atoms))]
            for j, x in labeled.items():
                if i != j and j not in not_minimals:
                    if len(e) < len(x):
                        for p in pair_set:
                            if p[0] == x[:len(p[0])] and p[1] == x[-len(p[1]):]:
                                not_minimals.append(j)

    return [i for i, e in labeled.items() if i not in not_minimals]               



if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option("-m", "--maude", dest="maude_path", help="path to maude")
    parser.add_option("-t", "--timeout", dest="timeout", type="int", help="timeout (seconds)")
    (options, args) = parser.parse_args()

    if options.maude_path != None:
        maude_path = os.path.join(options.maude_path, "maude")
        if not os.path.exists(maude_path):
            print("maude could not be found in the given path!")
            sys.exit()
    else:
        maude_path = exists_in_path("maude")
        if maude_path == None:
            print("maude could not be found in environment variables!")
            sys.exit()
    
    if len(args) < 1:
        print("Error: provide the argument <input_file>")
            
    network_file = args[0]
    if not is_json(network_file) and os.path.isfile(network_file):
        print("Please provide a .json file")
        sys.exit()
    
    with open(network_file) as f:
        network = json.load(f)



    start = time.time()

    manager = multiprocessing.Manager()
    processed_network = manager.dict()
    
    p = multiprocessing.Process(target=preprocess, args=(network, processed_network))
    p.start()

    terminated = True
    if options.timeout != None:
        p.join(options.timeout)

        if p.is_alive():
            print("The process has timed out.")
            p.terminate()
            terminated = False
    else:
        p.join()


    if terminated:
        manager = multiprocessing.Manager()
        final_result = manager.dict()
        
        p = multiprocessing.Process(target=equational, args=(processed_network,
                                                             final_result))
        p.start()

        if options.timeout != None:
            remaining_time = options.timeout - (time.time() - start)
            p.join(remaining_time)
        
            if p.is_alive():
                print("The process has timed out.")
                p.terminate()
                terminated = False
        else:
            p.join()


    if terminated:
        report, counter = report_result(final_result)  
        if counter > 1:
            minimal_violations = extract_minimal_traces(report)
            print("Minimal violations: # {}".format(', '.join(str(x) for x in minimal_violations)))
        
        end = time.time()
        time_elapsed = end - start
        print('Total of {} violation(s) found.\nTime elapsed: {:.2f} seconds.'.format(counter, time_elapsed))

        
    if os.path.exists(outfile):
        os.remove(outfile)



