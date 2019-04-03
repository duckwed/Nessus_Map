from __future__ import unicode_literals
from django.shortcuts import render, redirect
from django.conf import settings
from filebrowser.base import FileListing
from django.core.files.storage import FileSystemStorage
import xml.etree.ElementTree as ET
from Nessus_Parser.models import Hosts
from Nessus_Parser.models import Vulnerability
import json
import os

def generate_executive_report(request):
    print("in g-e-r")
    vulns = parse_all_xml()
    vulndict = dict()
    hostdict = dict()

    for risk in vulns:
        for vuln in vulns[risk]:
            vulndict[vuln] = dict()
            vulndict[vuln]["risk"] = risk
            vulndict[vuln]["name"] = vulns[risk][vuln]["name"]
            vulndict[vuln]["count"] = len(vulns[risk][vuln]["hosts"])

    sorted_d = sorted(vulndict, key=lambda x:vulndict[x]['count'], reverse=True)
    host_dict = dict()
    host_vuln_detail = dict()
    files = os.listdir(settings.MEDIA_ROOT)

    for file in files:
        path = os.path.join(settings.MEDIA_ROOT, file)
        host_dict, host_vuln_detail = do_host_vuln_parsing(path, host_dict, host_vuln_detail)

    return render(request, 'generate_executive.html', {'vulns' : vulndict, 'vulnOrder' : sorted_d, "host_dict": sorted(host_dict.items(), key=lambda value: value[1], reverse=True), "host_vuln_detail" : host_vuln_detail})


def handle_uploaded_file(myfile):
    with open(settings.MEDIA_ROOT, 'wb+') as destination:
        for chunk in myfile.chunks():
            destination.write(chunk)

def upload_file(request):
    return redirect('home')

def parse_XML(request):
    vulns = parse_all_xml()
    
    with open('vulns.json', 'w') as file:
        file.write(json.dumps(vulns))
    
    d2 = json.load(open("vulns.json"))
    return render(request, 'parsed_XML.html', {'vulns' : d2})

def parse_all_xml():
    vulns = dict()
    vulns['Critical'] = dict()
    vulns['High'] = dict()
    vulns['Medium'] = dict()
    vulns['Low'] = dict()
    vulns['None'] = dict()
    files = os.listdir(settings.MEDIA_ROOT)
    
    for file in files:
        path = os.path.join(settings.MEDIA_ROOT, file)
        vulns = do_vuln_parsing(vulns, path, file)
    
    return vulns

def do_vuln_parsing(vulns, path, filename):
    tree = ET.parse(path)
    for host in tree.findall('Report/ReportHost'):
        ipaddr = host.find("HostProperties/tag/[@name='host-ip']").text
        for item in host.findall('ReportItem'):
            risk_factor     = item.find('risk_factor').text
            pluginID        = item.get('pluginID')
            pluginName      = item.get('pluginName')
            port            = item.get('port')
            protocol        = item.get('protocol')
           
            plugin_output   = ""
            description     = ""
            synopsis        = ""
            see_also        = ""
            solution        = ""

            if item.find('plugin_output') is not None:
                plugin_output = item.find('plugin_output').text

            if item.find('description') is not None:
                description = item.find('description').text

            if item.find('synopsis') is not None:
                synopsis    = item.find('synopsis').text

            if item.find('see_also') is not None:
                see_also    = item.find('see_also').text

            if item.find('solution') is not None:
                solution    = item.find('solution').text

            ipaddr2 = "{0} ({1}/{2})".format(ipaddr, port, protocol)


            if pluginID in vulns['Critical'] or pluginID in vulns['High'] or pluginID in vulns['Medium'] or pluginID in vulns['Low'] or pluginID in vulns['None']:

                ip_entry_flag = False

                for ip in vulns[risk_factor][pluginID]['hosts']:
                    if ip[0] in ipaddr2:
                        ip_entry_flag = True
                        break

                if not ip_entry_flag:
                    vulns[risk_factor][pluginID]['hosts'].append([ipaddr2, plugin_output])

                if filename not in vulns[risk_factor][pluginID]['file']:
                     vulns[risk_factor][pluginID]['file'].append(filename)
            else:
                vulns[risk_factor][pluginID] = { 
                    'risk':risk_factor,
                    'name' : pluginName,
                    'synopsis': synopsis,
                    'see_also' : see_also,
                    'solution' : solution,
                    'file' : [filename],
                    'hosts' : [[ipaddr2,plugin_output]],
                    'pluginID': pluginID,
                    'description': description
                }
        
            
    return vulns

def do_port_filter(request):
    services = parse_services()
    return render(request, 'port_filter.html', {'services':services})

def parse_services():
    services = dict()
    files = os.listdir(settings.MEDIA_ROOT)
    for file in files:
        path = os.path.join(settings.MEDIA_ROOT, file)
        services = do_parse_services(services, path, file)
    return services

def do_parse_services(services, path, filename):
    tree = ET.parse(path)
    for host in tree.findall('Report/ReportHost'):
        ipaddr = host.find("HostProperties/tag/[@name='host-ip']").text
        for item in host.findall('ReportItem'):
            service = item.get('svc_name')
            port = item.get('port')
            protocol = item.get('protocol')
            ipaddr2 = "{0} ({1}/{2})".format(ipaddr, port, protocol)
            if service in services:
                if ipaddr2 not in services[service]:
                    services[service].append(ipaddr2)
            else:
                services[service] = [ipaddr2]
    return services


def do_parse_os(request):
    osDict = dict()
    files = os.listdir(settings.MEDIA_ROOT)
    for file in files:
        path = os.path.join(settings.MEDIA_ROOT, file)
        osDict = do_os_parsing(osDict, path, file)
    return render(request, 'parse_os.html', {'osDict' : osDict})
    


def do_os_parsing(osDict, path, filename):
    tree = ET.parse(path)
    
    for host in tree.findall('Report/ReportHost'):
        ipaddr = host.find("HostProperties/tag/[@name='host-ip']").text
        
        for item in host.findall('ReportItem'):
            pluginID        = item.get('pluginID')
            
            if pluginID != "33850" and pluginID != "108797" and pluginID != "84729" and pluginID != "97996" and pluginID != "73182" and pluginID != "88561" and pluginID != "108797":
                continue
            plugin_output   = ""
            
            if item.find('plugin_output') is not None:
                plugin_output = item.find('plugin_output').text
            
            if "support ended on" in plugin_output:
                plugin_output = plugin_output.split("support ended on")[0]
            
            if "The following Windows version is installed and not supported:" in plugin_output:
                plugin_output = plugin_output.split("The following Windows version is installed and not supported:")[1]
            osDict[ipaddr] = plugin_output
    
    return osDict


def do_host_vuln_parsing(path, host_dict, host_vuln_detail):
    tree = ET.parse(path)
    
    for host in tree.findall('Report/ReportHost'):
        ipaddr = host.find("HostProperties/tag/[@name='host-ip']").text
        
        if(ipaddr not in host_vuln_detail):
            host_vuln_detail[ipaddr] = dict()
            host_vuln_detail[ipaddr]["Critical"] = 0
            host_vuln_detail[ipaddr]["High"] = 0
            host_vuln_detail[ipaddr]["Medium"] = 0
            host_vuln_detail[ipaddr]["Low"] = 0
            host_vuln_detail[ipaddr]["Info"] = 0
        
        for item in host.findall('ReportItem'):
            risk_factor     = item.find('risk_factor').text
            
            if("Critical" in risk_factor):
                host_vuln_detail[ipaddr]["Critical"] = int(host_vuln_detail[ipaddr]["Critical"]) + 1
            
            elif("High" in risk_factor):
                host_vuln_detail[ipaddr]["High"] = host_vuln_detail[ipaddr]["High"] + 1
            
            elif("Medium" in risk_factor):
                host_vuln_detail[ipaddr]["Medium"] = host_vuln_detail[ipaddr]["Medium"] + 1
            
            elif("Low" in risk_factor):
                host_vuln_detail[ipaddr]["Low"] = host_vuln_detail[ipaddr]["Low"] + 1
            
            elif("None" in risk_factor):
                host_vuln_detail[ipaddr]["Info"] = host_vuln_detail[ipaddr]["Info"] + 1
            
            else:
                print(risk_factor)
        
        host_dict[ipaddr] = int(host_vuln_detail[ipaddr]["Critical"]) + int(host_vuln_detail[ipaddr]["High"]) + int(host_vuln_detail[ipaddr]["Medium"]) + int(host_vuln_detail[ipaddr]["Low"]) + int(host_vuln_detail[ipaddr]["Info"])
        
    return host_dict, host_vuln_detail
