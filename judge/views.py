import os
import resource
import subprocess

path_users_code = 'code_related/usersCode/'
standard_data = 'code_related/standard/'

'''
Side Note:
AC= All Clear
CTE= Compile Time Error
RTE= Runtime Error
'''

signals = {
    0:'AC',  # For Correct answer
    1:'CTE',  # compile time error, incase something is wrong with the code syntax
    256:'CTE',
    128:'CTE',
    127: 'CTE',
    # 256: 'C.T.E',
    2:'FILE_DOESN\'T_EXIST', #if the required file which you are processing isn't available at the required file location
    # P.S: All of these codes(exit codes of a process) are of the format 128 + signal code generated by child process

    159:'AT',  # 31 SIGSYS (When system call doesn't match)
    135:'AT',  # Bus error 7 int x[10000000000000]
    136:'RTE',  # SIGFPE sig -> 8 floating point exception
    139:'RTE',  # (128 + 11) -> 11 SIGSEGV (Invalid memory reference)
    137:'TLE',  # Time limit exceeded or Resource limit exceeded killed by setprlimit

    'wa': 'WA',  # Wrong answer, custom code defined by us only used for comparing user's code o/p with test case output.
}

#comparing the output of the ideal answer to the user's code answer:
def compare(user_output, expected_output):
    user = open(user_output, "r")
    expected = open(expected_output, "r")

    lines_user = user.read()
    print(lines_user)
    lines_user=lines_user.rstrip()
    lines_expected = expected.read()
    lines_expected=lines_expected.rstrip()
    user.close()
    expected.close()

    if lines_user == lines_expected: # i.e. the output matches the expected output for the particular testcase
        return 0
    else:
        return 'wa'

# method to read the quota files to
def get_resource_limits(qno, test_case_no,lang):

    if(lang=="py"): # allocating additional resources tp python codes as Python is a slower executing and more resource consuming language.
        resource_limit_path = standard_data + 'quotas/question{}/pyquota{}.txt'.format(qno, test_case_no)
    else:
        resource_limit_path = standard_data + 'quotas/question{}/quota{}.txt'.format(qno, test_case_no)

    description_file = open(resource_limit_path)

    lines = description_file.readlines() # reading the file containing the
    time = lines[0].strip() # time limit to be allocated for particular testcase
    mem = lines[1].strip()  # memory limit to be allocated for particular testcase

    resource_limits = {
        'time': float(time),
        'mem': int(mem),
    }
    return resource_limits #returning the resource limits in the form of a dictionary response



def resource_allocation(quota):
    cpu_time = quota['time']
    mem = quota['mem']

    def setlimits():
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_time, cpu_time))
        resource.setrlimit(resource.RLIMIT_AS, (mem, mem))
        

    return setlimits



def compile_code(user_question_path, code_file_path, err_file,lang): #for c and cpp codes only
    
    print("User err path:", err_file)

    '''
    Leveraging the Linux Terminal Subsystem of the host server for compiling the .c and .cpp code files 
    via gcc by creating an executable while adhering to the libseccomp rules and incase of errors writing them to the error.txt file
    as given incase of standard error as specified by the seccomp
    '''
    if lang == 'c':
        rc = os.system(
            "gcc" + " -o " + user_question_path + 'exe ' + code_file_path + ' -lseccomp ' + '-lm 2>' + err_file)
    else:
        print("in cpp")
        rc = os.system(
            "g++" + " -o " + user_question_path + 'exe ' + code_file_path + ' -lseccomp ' + '-lm 2>' + err_file)
    print("rc",rc)
    return rc  # return 0 for successful compilation and 1 for errors during compilation



def run_in_sandbox(exec_path, lang, ipfile, opfile, errorfile, quota):

    '''
    For more info about the subprocess module:
    https://docs.python.org/3/library/subprocess.html
    '''
    if lang == 'py':
        child = subprocess.Popen(
            ['python3 ' + exec_path], preexec_fn=resource_allocation(quota),  # preexec_fn specifies a child process of the main process, i.e resource allocation in this case
            stdin=ipfile, stdout=opfile, stderr=errorfile, shell=True
        )
    else:
        child = subprocess.Popen(
            ['./' + exec_path], preexec_fn=resource_allocation(quota),
            stdin=ipfile, stdout=opfile, stderr=errorfile, shell=True
        )

    child.wait() # wait for the process to terminate
    rc = child.returncode #The child return code. A None value indicates that the process hasn’t terminated yet.

    if rc < 0:
        return 128 - rc
    else:
        return rc


def runtc(test_case_no,user_que_path,code_file_path,lang,qno,custominput):
    if custominput==True:
        input_file=user_que_path+"custominput.txt"
    else:
        input_file=standard_data+'input/question{}/input{}.txt'.format(qno,test_case_no)

    input_file=open(input_file,'r')

    user_output=user_que_path+'output{}.txt'.format(test_case_no)
    user_op_file=open(user_output,"w+")

    quota=get_resource_limits(qno,test_case_no,lang)

    error_path=user_que_path+'error.txt'
    error_file=open(error_path,'w+')

    if lang == 'py':
        exec_file = code_file_path

    else:
        exec_file = user_que_path + 'exe'

    process_code = run_in_sandbox(exec_file,lang,input_file,user_op_file,error_file,quota)

    input_file.close()
    user_op_file.close()
    error_file.close()

    e_output_file = standard_data + 'output/question{}/expected_output{}.txt'.format(qno, test_case_no)

    if process_code == 0:
        if(test_case_no!=0):
            result_value = compare(user_output, e_output_file)
            return result_value

    return process_code


def exec(username, qno, lang, test_cases=1, custominput=False, run=False):
    print("in exec")
    user_question_path = path_users_code + '{}/question{}/'.format(username, qno)
    if run:
        code_file=user_question_path+'code.{}'.format(lang)
    else:
        code_file = user_question_path + 'code{}.{}'.format(1,lang) #change attempts to db value later

    py_sandbox='judge/pysand.py'

    with open(user_question_path + 'temp.py', 'w+') as file:
        sand = open(py_sandbox, 'r')
        file.write(sand.read())
        sand.close()

    error_file=user_question_path+'error.txt'

    result_codes=[]


    if(lang!='py'):
        print("in compile code")
        compilestat=compile_code(user_question_path, code_file, error_file,lang)
        print("compilestat: ",compilestat)
        if(compilestat!=0):
            result_codes=["CTE"]*test_cases
            print("resultcodes",result_codes)
            return result_codes


    if run: #i.e. only running the code to test and not submit
        process_code = runtc(
            test_case_no=0, # 0 corresponds to the sample input testcase, as default value
            user_que_path=user_question_path,
            code_file_path=code_file,
            lang=lang,
            qno=qno,
            custominput=custominput,
        )

        print("Process Code for the following code run:", process_code)
        result_codes.append(signals[process_code])

    else:
        # iterating over the test cases, during code submission
        for i in range(1, test_cases+1):
            process_code = runtc(
                test_case_no=i,
                user_que_path=user_question_path,
                code_file_path=code_file,
                lang=lang,
                qno=qno,
                custominput=custominput,
            )

            print("Process Code for the Testcase",i,":",process_code)
            result_codes.append(signals[process_code])
            

    return result_codes
