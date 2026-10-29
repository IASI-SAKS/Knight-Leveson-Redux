#!/bin/bash

PCOV_FILE="coverage-new.txt"
ALTERNATIVE_IMPLEMENTATIONS_FILE="alternativeImplementations-new.txt"
IMPLEMENTATION_DEPENDENT_TESTSUITE_DIR="ImplementationDependentTestSuites-new"
IMPLEMENTATION_INDEPENDENT_TESTSUITE_FILE="implementationIndependentTestSuite-new.txt"

GENERATE_IMPLEMENTATION_INDEPENDENT_TESTSUITE="NO"

IMPLEMENTATION_INDEPENDENT_TESTSUITE_SIZE=10;
IMPLEMENTATION_DEPENDENT_TESTSUITE_SIZE=10;

POSITIONAL_ARGS=()

while [[ $# -gt 0 ]]; do
  case $1 in
    -c|--coverage_file)
      PCOV_FILE="$2"
      shift # past argument
      shift # past value
      ;;
    -f|--independet_file)
      IMPLEMENTATION_INDEPENDENT_TESTSUITE_FILE="$2"
      shift # past argument
      shift # past value
      ;;
    -F|--alt_impls_file)
      ALTERNATIVE_IMPLEMENTATIONS_FILE="$2"
      shift # past argument
      shift # past value
      ;;
    -i|--independet_size)
      IMPLEMENTATION_INDEPENDENT_TESTSUITE_SIZE="$2"
      shift # past argument
      shift # past value
      ;;
    -d|--dependet_size)
      IMPLEMENTATION_DEPENDENT_TESTSUITE_SIZE="$2"
      shift # past argument
      shift # past value
      ;;
    -D|--dependet_target_dir)
      IMPLEMENTATION_DEPENDENT_TESTSUITE_DIR="$2"
      shift # past argument
      shift # past value
      ;;
    -a|--gen_all)
      GENERATE_IMPLEMENTATION_INDEPENDENT_TESTSUITE="YES"
      shift # past argument
      ;;
    -h|--help)
      echo "$1 [-f|--coverage_file <coverage_file>] [-i|--independet_size size] [-d|--dependet_size size] [-a|--gen_all]"
      echo "Note that the IMPLEMENTATION INDEPENDENT_TESTSUITE is generated **ONLY** when the option \"-a|--gen_all\" is passed to $0"
      exit 1
      ;;
    -*|--*)
      echo "Unknown option $1"
      echo "Run: $0 --help"
      exit 1
      ;;
    *)
      POSITIONAL_ARGS+=("$1") # save positional arg
      shift # past argument
      ;;
  esac
done

TMP_FILE=`mktemp`
grep "__run000" ${PCOV_FILE} > ${ALTERNATIVE_IMPLEMENTATIONS_FILE}

if [ ! -d "$DIRECTORY" ]
then
  echo "${IMPLEMENTATION_DEPENDENT_TESTSUITE_DIR} does not exist. Creating it ..."
  mkdir ${IMPLEMENTATION_DEPENDENT_TESTSUITE_DIR}
  echo "... done"
fi

ALTERNATIVE_IMPLEMENTATIONS_COUNTER=0
for ALT in `cat ${ALTERNATIVE_IMPLEMENTATIONS_FILE}`
do
  ((ALTERNATIVE_IMPLEMENTATIONS_COUNTER++))
  echo ${ALTERNATIVE_IMPLEMENTATIONS_COUNTER}
  IMPLEMENTATION_DEPENDENT_TESTSUITE_FILE="${IMPLEMENTATION_DEPENDENT_TESTSUITE_DIR}/${ALTERNATIVE_IMPLEMENTATIONS_COUNTER}-${ALT}.txt"
  echo "${ALT} --> ${IMPLEMENTATION_DEPENDENT_TESTSUITE_FILE}"
#   sed -n "/^${ALT}/,/^$/p" ${PCOV_FILE}| grep "test_id" | grep "lines= [8].\." | grep -v "lines= 9.\." | shuf | head -n ${IMPLEMENTATION_DEPENDENT_TESTSUITE_SIZE} | sort > ${IMPLEMENTATION_DEPENDENT_TESTSUITE_FILE}
  sed -n "/^${ALT}/,/^$/p" ${PCOV_FILE}| grep "test_id" | grep "lines= [4567].\." | grep -v "lines= 4[01234]\." | grep -v "lines= 7[6789]\." | shuf | head -n ${IMPLEMENTATION_DEPENDENT_TESTSUITE_SIZE} | sort > ${IMPLEMENTATION_DEPENDENT_TESTSUITE_FILE}
  TEST_LIST_SIZE=`cat ${IMPLEMENTATION_DEPENDENT_TESTSUITE_FILE} | wc -l`
  echo "TEST SUITE SIZE: ${TEST_LIST_SIZE}"
 
  cat ${IMPLEMENTATION_DEPENDENT_TESTSUITE_FILE} >> ${TMP_FILE}
  
done

if [[ "${GENERATE_IMPLEMENTATION_INDEPENDENT_TESTSUITE}" = "YES" ]]
then
  HUGE_TESTSUITE_FILE="hugeImplementationIndependentTestSuite.txt"

  TMP_FILE2=`mktemp`
  cat ${TMP_FILE} | cut -d "|" -f 1 | sort -u > ${TMP_FILE2}
  mv ${TMP_FILE2} ${TMP_FILE}

  grep "test_id" ${PCOV_FILE} | cut -d "|" -f 1 | sed "s/[[:blank:]]\+$//" | sort -u > ${HUGE_TESTSUITE_FILE}
  
  for item in `sed "s/ /§/g" ${TMP_FILE}`
  do
    correctItem=`echo ${item} | sed "s/§\+$//" | sed "s/§/ /g"`
#     echo "*******************************"
#     echo "item: ${item}"
#     echo "correctItem: ${correctItem}"
#     grep -v "${correctItem}" ${HUGE_TESTSUITE_FILE}
#     echo "*******************************"
    grep -v "${correctItem}" ${HUGE_TESTSUITE_FILE} > ${TMP_FILE2}
    mv ${TMP_FILE2} ${HUGE_TESTSUITE_FILE}    
  done
  
  cat ${HUGE_TESTSUITE_FILE} | shuf | head -n ${IMPLEMENTATION_INDEPENDENT_TESTSUITE_SIZE} > ${IMPLEMENTATION_INDEPENDENT_TESTSUITE_FILE}
  
  rm ${HUGE_TESTSUITE_FILE}
fi  

